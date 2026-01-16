class Handleambiguity :
    def __init__ (self):
        pass

    def handle(self, tokens_with_tags):
        tokens = [token for token, tag in tokens_with_tags]
        pos_tags = [tag for token, tag in tokens_with_tags]

        fixed_indices = set()

        for idx, (token, tag) in enumerate(tokens_with_tags):
            if idx in fixed_indices:
                continue

            if tag == "PRP-DEM" and token.lower() in {"itu", "ini", "tersebut", "demikian"}:
                prp_or_dt = self.handle_prpdem_vs_dtdef(token, idx, pos_tags)
                if prp_or_dt and prp_or_dt != tag:
                    pos_tags[idx] = prp_or_dt
                    fixed_indices.add(idx)
                    continue

            if tag.startswith("NN") and token.lower() in {"air", "tepung", "gula", "beras"}:
                noun_type = self.handle_mass_vs_common(token, idx, tokens, pos_tags)
                if noun_type and noun_type != tag:
                    pos_tags[idx] = noun_type
                    fixed_indices.add(idx)
                    continue

            if token.lower() == "sama":
                sama_tag = self.handle_sama(token, idx, tokens, pos_tags)
                if sama_tag and sama_tag != tag:
                    pos_tags[idx] = sama_tag
                    fixed_indices.add(idx)
                    continue

            if token.lower() == "baik":
                jj_quality = self.handle_jjquality_vs_conjunctions(token, idx, tokens, pos_tags)
                if jj_quality and jj_quality != tag:
                    pos_tags[idx] = jj_quality
                    fixed_indices.add(idx)
                    continue

            if token.lower() in {"sejak", "hingga", "selama", "sewaktu"}:
                subord_tag = self.handle_consub_vs_intemp(token, idx, pos_tags)
                if subord_tag and subord_tag != tag:
                    pos_tags[idx] = subord_tag
                    fixed_indices.add(idx)
                    continue

            if token.lower() in {"malah", "justru"}:
                mod_emph = self.handle_modemph_vs_modasp(token, idx, tokens, pos_tags)
                if mod_emph and mod_emph != tag:
                    pos_tags[idx] = mod_emph
                    fixed_indices.add(idx)
                    continue

            if token.lower() in {"sedikit", "lumayan"}:
                mod_degr = self.handle_adv_vs_dt_vs_jj(token, idx, tokens, pos_tags)
                if mod_degr and mod_degr != tag:
                    pos_tags[idx] = mod_degr
                    fixed_indices.add(idx)
                    continue

        self.handle_demonstrative_disambiguation(tokens, pos_tags)
        return list(zip(tokens, pos_tags))

    def handle_prpdem_vs_dtdef(self, token, idx, pos_tags):
        prev_tag = pos_tags[idx - 1][1] if idx > 0 else ''
        next_tag = pos_tags[idx + 1][1] if idx + 1 < len(pos_tags) else ''
        next_next_tag = pos_tags[idx + 2][1] if idx + 2 < len(pos_tags) else ''

        if (next_tag and next_tag.startswith('NN')) or (prev_tag and prev_tag.startswith('NN')):
            pos_tags[idx] = (token, 'DT-DEF')
            return 'DT-DEF'

        if idx == 0 or (not next_tag and not prev_tag):
            pos_tags[idx] = (token, 'PRP-DEM')
            return 'PRP-DEM'

        if not next_tag or not next_tag.startswith('NN'):
            pos_tags[idx] = (token, 'PRP-DEM')
            return 'PRP-DEM'

        pos_tags[idx] = (token, 'DT-DEF')
        return "<UNK>"

    def handle_mass_vs_common(self, token, idx, tokens, pos_tags):
        prev_tag = pos_tags[idx - 1] if idx > 0 else ''
        next_tag = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ''
        next_next_tag = pos_tags[idx + 2] if idx + 2 < len(pos_tags) else ''

        current_tag = pos_tags[idx]
        if not current_tag.startswith('NN'):
            return "<UNK>"

        if prev_tag.startswith('VB'):
            return 'NN-MASS'
            
        if next_tag.startswith('JJ') or next_next_tag.startswith('JJ'):
            return 'NN-MASS'

        if next_tag.startswith('DT') and not next_next_tag.startswith('JJ'):
            return 'NN-COM'

        return current_tag
    
    def handle_sama(self, token, idx, tokens, pos_tags):
        prev_tag = pos_tags[idx - 1] if idx > 0 else ''
        next_tag = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ''
        next_next_tag = pos_tags[idx + 2] if idx + 2 < len(pos_tags) else ''

        if (next_tag and next_tag.startswith("MOD")) or (next_tag in {"MOD-NEG", "ADV-ATT"}):
            pos_tags[idx] = "MOD-EMPH"
            return "MOD-EMPH"

        if prev_tag and prev_tag.startswith("VB"):
            pos_tags[idx] = "IN-COM"
            return "IN-COM"

        if next_tag and (next_tag.startswith("PRP") or next_tag.startswith("NN")):
            pos_tags[idx] = "IN-COM"
            
        if (prev_tag and prev_tag.startswith("JJ")) or (next_tag and next_tag.startswith("JJ")):
            pos_tags[idx] = "JJ-QUALITY"
            return "JJ-QUALITY"

        pos_tags[idx] = "JJ-QUALITY"
        return "JJ-QUALITY"

    def handle_consub_vs_intemp(self, token, idx, pos_tags):
        """
        Mengubah label CON-SUB dari regex menjadi IN-TEMP jika konteks menunjukkan fungsi temporal.
        """
        prev_tag = pos_tags[idx - 1] if idx > 0 else ''
        next_tag = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ''
        next_next_tag = pos_tags[idx + 2] if idx + 2 < len(pos_tags) else ''

        temporal_indicators = {
            "VB-ACT", "VB-STAT", "VB-CAUS", "VB-MODL", "VB-TENSE", 
            "MOD-TEMP", "DT-ORD", "DT-CARD", "Q-TEMP", "IN-TEMP"
        }

        for tag in (next_tag, next_next_tag):
            if tag and any(tag.startswith(ind) for ind in temporal_indicators):
                return "IN-TEMP"

        return "CON-SUB"

    def handle_jjquality_vs_conjunctions(self, token, idx, tokens, pos_tags):
        prev_pos = pos_tags[idx - 1] if idx > 0 else ""
        next_pos = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ""
        current_pos = pos_tags[idx]

        if current_pos == "JJ-QUALITY" and (prev_pos == "CON-COR" or next_pos == "CON-COR"):
            return "CON-COR"

        if current_pos == "JJ-QUALITY":
            return "JJ-QUALITY"

        return None

    def handle_modemph_vs_modasp(self, token, idx, tokens, pos_tags):
        prev_pos = pos_tags[idx - 1] if idx > 0 else ""
        next_pos = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ""
        current_pos = pos_tags[idx]

        if current_pos == "MOD-EMPH" or current_pos == "MOD-ASP":
            if prev_pos.startswith("VB") or next_pos.startswith("VB"):
                return "MOD-ASP"
            if prev_pos.startswith("MOD") or next_pos.startswith("MOD"):
                return "MOD-EMPH"
            if prev_pos.startswith("NN") or next_pos.startswith("NN"):
                return "MOD-EMPH"
            return "MOD-EMPH"

        return None

    def handle_adv_vs_dt_vs_jj(self, token, idx, tokens, pos_tags):
        current_pos = pos_tags[idx]

        if current_pos.startswith("NN"):
            return None

        prev_pos = pos_tags[idx - 1] if idx > 0 else ""
        next_pos = pos_tags[idx + 1] if idx + 1 < len(pos_tags) else ""

        if prev_pos.startswith("DT") and next_pos.startswith("NN"):
            return "JJ-QUALITY" 

        if next_pos.startswith("JJ"):
            return "ADV-ATT"

        if prev_pos.startswith("VB"):
            return "JJ-QUALITY"

        if next_pos.startswith("NN"):
            return "DT-INDEF"

        return "AVD-ATT" 

    
    def handle_demonstrative_disambiguation(self, tokens, tags):
        demonstratives = {'ini', 'itu', 'tersebut'}
        
        for i, (token, tag) in enumerate(zip(tokens, tags)):
            token_lower = token.lower()
            if token_lower in demonstratives:
                tag = 'PRP-DEM'

                if i + 1 < len(tokens):
                    next_tag = tags[i + 1] if i + 1 < len(tags) else ''
                    if next_tag.startswith('NN') or next_tag.startswith('JJ'):
                        tag = 'DT-DEF'

                if i > 0:
                    prev_tag = tags[i - 1]
                    if prev_tag.startswith('VB') or prev_tag.startswith('IN'):
                        tag = 'PRP-DEM'

                tags[i] = tag
        return tags
