class KeyboardLayout:
    def __init__(self, desk_dims):
        self.width, self.height = desk_dims
        self.rows = [
            "QWERTYUIOP",
            "ASDFGHJKL",
            "ZXCVBNM"
        ]
        self.keys = self._generate_layout()

    def _generate_layout(self):
        layout = {}
        
        # We'll put the keyboard in the lower 60% of the desk area
        kb_top = 0.4 
        kb_height = 0.5
        row_h = kb_height / 4
        
        # Row 1 (Q-P)
        y = kb_top
        key_w = 1.0 / 10
        for i, char in enumerate(self.rows[0]):
            layout[char] = [i * key_w, y, (i+1) * key_w, y + row_h]
            
        # Row 2 (A-L) - Slightly indented
        y += row_h
        indent = 0.05
        key_w = (1.0 - indent*2) / 9
        for i, char in enumerate(self.rows[1]):
            layout[char] = [indent + i * key_w, y, indent + (i+1) * key_w, y + row_h]
            
        # Row 3 (Z-M) - More indented
        y += row_h
        indent = 0.1
        key_w = (1.0 - indent*2) / 7
        for i, char in enumerate(self.rows[2]):
            layout[char] = [indent + i * key_w, y, indent + (i+1) * key_w, y + row_h]
            
        # Row 4 (Space)
        y += row_h
        space_w = 0.4
        layout[" "] = [0.5 - space_w/2, y, 0.5 + space_w/2, y + row_h]
        
        return layout

    def get_key_at(self, x_desk, y_desk):
        # Convert to relative
        rx = x_desk / self.width
        ry = y_desk / self.height
        
        for char, bbox in self.keys.items():
            x1, y1, x2, y2 = bbox
            if x1 <= rx <= x2 and y1 <= ry <= y2:
                return char
        return None
