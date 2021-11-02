from pathlib import Path


class FilterModule:

    def filters(self):
        return {
            'path': self.path,
        }

    def path(self, path):
        return Path(path)
