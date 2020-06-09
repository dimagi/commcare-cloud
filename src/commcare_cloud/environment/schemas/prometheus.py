import jsonobject


class PrometheusConfig(jsonobject.JsonObject):
    prometheus_monitoring_enabled = jsonobject.BooleanProperty(required=True)
    grafana_security = jsonobject.DictProperty()

    def to_generated_variables(self):
        variables = self.to_json()
        return variables
    
   
