import jsonobject

class PrometheusConfig(jsonobject.JsonObject):
    prometheus_monitoring_enabled = jsonobject.BooleanProperty()
    
    def check(self):
        variables = self.to_json().keys()
        if variables:
            if 'grafana_security'  in str(variables):
                return
            else:
                raise KeyError("Missing Key grafana_security in prometheus.yml")

    def to_generated_variables(self):
        variables = self.to_json()
        return variables
    
   