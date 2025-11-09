import json
import os

class OdaiRepository:
    def __init__(self, json_path):
        self.json_path = json_path
        os.makedirs(os.path.dirname(json_path), exist_ok=True)
        if not os.path.exists(json_path):
            with open(json_path, "w") as f:
                json.dump([], f)

    def load(self):
        with open(self.json_path, "r") as f:
            return json.load(f)  # ✅ dictのまま返す

    def save(self, odai_list):
        with open(self.json_path, "w") as f:
            json.dump(odai_list, f, ensure_ascii=False, indent=2)

    def file_exists(self, filename):
        return any(o.get("file") == filename for o in self.load())
