from __future__ import unicode_literals
def get_new_resource_address(environment, old_resource_address):
    if old_resource_address == 'module.ga_alb_waf.aws_iam_role.firehose_role':
        return 'module.ga_alb_waf.module.firehose_stream.aws_iam_role.firehose_role'
    elif old_resource_address == 'module.ga_alb_waf.aws_iam_role_policy.firehose_role':
        return 'module.ga_alb_waf.module.firehose_stream.aws_iam_role_policy.firehose_role'
    elif old_resource_address == 'module.ga_alb_waf.aws_kinesis_firehose_delivery_stream.front_end_waf_logs':
        return 'module.ga_alb_waf.module.firehose_stream.aws_kinesis_firehose_delivery_stream.firehose_stream'
