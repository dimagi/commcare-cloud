def get_new_resource_address(environment, old_resource_address):
    if old_resource_address == 'module.ga_alb_waf.aws_s3_bucket.front_end_alb_logs':
        return 'module.logshipping.aws_s3_bucket.log_bucket'
