from os.path import basename


class FilterModule:

    def filters(self):
        return {'release_names': self.release_names}

    def release_names(self, hostvars, play_hosts):
        """Aggregate release names from play_hosts

        Returns a list of releases that are common to all play hosts.
        """
        def nameset(vars):
            return {basename(f["path"]) for f in vars["releases"]["files"]}
        if not (play_hosts and all("releases" in hostvars[h] for h in play_hosts)):
            return []
        return sorted(set.intersection(*[nameset(hostvars[h]) for h in play_hosts]))
