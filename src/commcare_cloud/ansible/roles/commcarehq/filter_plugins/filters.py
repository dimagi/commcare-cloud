class FilterModule:
    def filters(self):
        return {"env_vars": self.env_vars}

    def env_vars(self, namespaces):
        """Generate (name, value) pairs of the "env_vars" dict from each namespace

        If multiple namespaces' env_vars contain the same variable, the
        last namespace wins. Variables with a value of `None` or empty
        string will be ignored.
        """
        seen = set()
        for ns in reversed(namespaces):
            try:
                env_vars = ns['env_vars']
            except (KeyError, TypeError):
                env_vars = getattr(ns, "env_vars", {})
            for name, value in env_vars.items():
                if name in seen:
                    continue
                seen.add(name)
                if value is not None and str(value).strip():
                    yield name, str(value)
