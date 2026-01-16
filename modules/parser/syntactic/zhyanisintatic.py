import logging
import os

from preprocessing.nlp.parser.parse_data import cfg, clause_boundary, coordination_patern, treebank
from preprocessing.nlp.parser.sintatic.module import chunking

class ZhyaniSyntacticParser:
    def __init__(self):
        self.cfg = cfg
        self.clause_boundary = clause_boundary

        self.load()

        logging.basicConfig(level=logging.INFO)

        self.chunking = chunking.Chunking()

    def syntactic_parse(self, tokens):
        chunks = self._safe_chunking(tokens)

        clause_boundaries = self._safe_clause_detection(tokens)

        final_tree = ('S', chunks)

        self._safe_analysis(final_tree, chunks)

        return final_tree

    def _safe_chunking(self, tokens):
        try:
            if hasattr(self, 'pre_parse_chunking'):
                chunks = self.pre_parse_chunking(tokens)

                if chunks is not None and isinstance(chunks, list):
                    return chunks
                    
        except Exception as e:
            pass
            
        return tokens

    def _safe_clause_detection(self, tokens):
        try:
            if hasattr(self, 'detect_clause_boundary'):
                return self.detect_clause_boundary(tokens)
        except Exception:
            pass
        return []

    def _safe_analysis(self, tree, chunks):
        try:
            if hasattr(self, 'get_constituents'):
                self.get_constituents(tree)
            
            if hasattr(self, 'annotate_depth_and_level'):
                self.annotate_depth_and_level(chunks)
        except Exception:
            pass

    def match_rule(self, lhs, rhs_labels):
        if lhs not in self.cfg_rules:
            return False

        for production in self.cfg_rules[lhs]:
            if len(production) != len(rhs_labels):
                continue

            match = True
            for expected, actual in zip(production, rhs_labels):
                if expected == actual:
                    continue
                elif expected in self.cfg_rules:
                    possible_tags = [item[0] for item in self.cfg_rules[expected]]
                    if actual not in possible_tags:
                        match = False
                        break
                else:
                    match = False
                    break

            if match:
                return True

        return False

    def get_constituents(self, tree):
        if tree is None:
            return [], 0
        
        constituents = []

        def is_subtree(node):
            return isinstance(node, tuple) and len(node) > 1 and isinstance(node[1], (list, tuple)) and not isinstance(node[1], str)

        def traverse(node, pos):
            if isinstance(node, str):
                return pos + 1, 1, node

            label = node[0]
            children = node[1]
            start = pos
            total_tokens = 0
            collected_subtree = []

            for child in children:
                if isinstance(child, tuple) and isinstance(child[1], str):
                    collected_subtree.append((child[0], child[1]))
                    pos += 1
                    total_tokens += 1
                else:
                    pos, child_tokens, sub = traverse(child, pos)
                    total_tokens += child_tokens
                    collected_subtree.append(sub)

            end = pos
            subtree = (label, collected_subtree)
            constituents.append((label, start, end, subtree))
            return end, total_tokens, subtree

        _, total_leaf_count, _ = traverse(tree, 0)
        return constituents, total_leaf_count

    def is_valid_structure(self, lhs, rhs_labels):
        if lhs not in self.cfg:
            return False

        clean_labels = []
        for label in rhs_labels:
            if isinstance(label, tuple):
                label = label[0]
            if not str(label).startswith("CON-"):
                clean_labels.append(label)

        for production in self.cfg[lhs]:
            if len(production) != len(clean_labels):
                continue
            if all(
                expected == actual or str(actual).startswith(expected + "-")
                for expected, actual in zip(production, clean_labels)
            ):
                return True

        return False

    def detect_clause_boundary(self, tokens):
        boundaries = []
        start = 0

        for i, chunk in enumerate(tokens):
            if isinstance(chunk, tuple) and isinstance(chunk[1], list):
                label = chunk[0]
                if label == 'VP' and i > start:
                    boundaries.append((start, i))
                    start = i
            else:
                token, label = chunk
                if label.startswith("CON-") and i > start:
                    boundaries.append((start, i))
                    start = i

        if start < len(tokens):
            boundaries.append((start, len(tokens)))

        return boundaries

    def pre_parse_chunking(self, tokens):
        all_chunks = []
        segments = []
        buffer = []

        for token in tokens:
            buffer.append(token)
            tag = token[1]
            if tag.startswith("SYM-COM") or tag.startswith("SYM-DOT") or tag.startswith("CON-"):
                segments.append(buffer)
                buffer = []
        if buffer:
            segments.append(buffer)

        for segment in segments:
            i = 0
            while i < len(segment):
                try:
                    if isinstance(segment[i], tuple) and isinstance(segment[i][1], list):
                        all_chunks.append(segment[i])
                        i += 1
                        continue

                    token, tag = segment[i]
                    main_tag = tag.split("-")[0]
                    
                    chunk_result = None
                    
                    if self.chunking.is_np_token(tag) and (i == 0 or not segment[i - 1][1].startswith("IN")):
                        chunk_result = self.chunking.build_np(segment, i)

                    elif main_tag == "VB" or (tag in {"MOD-TEMP", "MOD-ACT"} and i + 1 < len(segment) and segment[i + 1][1].startswith("VB")):
                        chunk_result = self.chunking.build_vp(segment, i)

                    elif tag.startswith("IN"):
                        chunk_result = self.chunking.build_pp(segment, i)

                    elif self.chunking.is_adjp_token(tag) and not tag.startswith("MOD"):
                        chunk_result = self.chunking.build_adjp(segment, i)

                    elif self.chunking.is_advp_token(tag):
                        chunk_result = self.chunking.build_advp(segment, i)
                    
                    elif self.chunking.is_wh_token(tag):
                        chunk_result = self.chunking.build_interrog(segment, i)

                    if chunk_result:
                        chunk, new_i = chunk_result
                        all_chunks.append(chunk)
                        i = new_i
                    else:
                        if main_tag == "CON":
                            all_chunks.append(('CONJ', [segment[i]]))
                            i += 1
                        elif main_tag == "INT":
                            all_chunks.append(('INTJ', [segment[i]]))
                            i += 1
                        elif main_tag == "SYM":
                            all_chunks.append(('PUNCT', [segment[i]]))
                            i += 1
                        else:
                            all_chunks.append(segment[i])
                            i += 1

                except Exception as e:
                    if i < len(segment):
                        all_chunks.append(segment[i])
                    i += 1

        return all_chunks
    
    def annotate_depth_and_level(self, chunks, current_depth=0, sentence=1, parent=None):
        annotated = []

        for chunk in chunks:
            if isinstance(chunk, tuple):
                label, content = chunk

                if isinstance(content, list):
                    annotated.append({
                        "sentence": sentence,
                        "depth": current_depth,
                        "label": label,
                        "parent": parent,
                        "content": content
                    })

                    child_annotated = self.annotate_depth_and_level(content, current_depth + 1, sentence + 1, label)
                    annotated.extend(child_annotated)
                else:
                    continue

        return annotated

class ppront:
    @staticmethod
    def pretty_print_to_file(parse_result, output_txt_path):
        def pretty(chunk, indent=0):
            tab = "    "

            if isinstance(chunk, tuple) and isinstance(chunk[1], list):
                s = f"{tab * indent}('{chunk[0]}', [\n"
                for c in chunk[1]:
                    s += pretty(c, indent + 1) + ",\n"
                s += f"{tab * indent}])"
                return s
            elif isinstance(chunk, tuple):
                return f"{tab * indent}{repr(chunk)}"
            else:
                return f"{tab * indent}{str(chunk)}"

        try:
            os.makedirs(os.path.dirname(output_txt_path), exist_ok=True)
            with open(output_txt_path, "w", encoding="utf-8") as f:
                for chunk in parse_result:
                    f.write(pretty(chunk) + "\n")
            print(f"[UPDATE]\n>> {os.path.abspath(output_txt_path)}\n")
        except FileNotFoundError:
            print(f"[PANIC] '{output_txt_path}'")
        except Exception as e:
            print(f"[ERROR] {e}\nFix kamu ngerusak sesuatu tanpa sadar.")



    
