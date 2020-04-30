import jsonobject


class PrometheusConfig(jsonobject.JsonObject):
    prometheus_monitoring_enabled = jsonobject.BooleanProperty()
    grafana_security = jsonobject.DictProperty(required=True)

    def to_generated_variables(self):
        variables = self.to_json()
        return variables
    
   