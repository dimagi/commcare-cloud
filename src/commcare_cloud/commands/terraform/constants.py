# Paste the output of the commcare-hq management command
#
#   ./manage.py list_waf_allow_patterns
#
# to replace the contents of the multiline string
COMMCAREHQ_XML_POST_URLS_REGEX = r"""
^/a/([\w\.:-]+)/api/case/v2(?:/([\w\-,]+))?/?$
^/a/([\w\.:-]+)/api/case/v2/bulk-fetch/$
^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$
^/a/([\w\.:-]+)/api/v0\.6/case(?:/([\w\-,]+))?/?$
^/a/([\w\.:-]+)/api/v0\.6/case/bulk-fetch/$
^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/app_logo/([\w\-]+)/$
^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/audio/$
^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/bulk/$
^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/image/$
^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/video/$
^/a/([\w\.:-]+)/apps/edit_advanced_form_actions/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/apps/edit_form_attr/([\w-]+)/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/apps/edit_form_attr_api/([\w-]+)/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/apps/edit_module_detail_screens/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/apps/patch_xform/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/apps/view/([\w-]+)/languages/bulk_app_translations/upload/$
^/a/([\w\.:-]+)/cloudcare/api/readable_questions/$
^/a/([\w\.:-]+)/cloudcare/apps/report_formplayer_error
^/a/([\w\.:-]+)/cloudcare/apps/report_sentry_error
^/a/([\w\.:-]+)/data/export/custom/download_data_files/$
^/a/([\w\.:-]+)/data_dictionary/import$
^/a/([\w\.:-]+)/dhis2/map/(\w+)/$
^/a/([\w\.:-]+)/fixtures/edit_lookup_tables/upload/$
^/a/([\w\.:-]+)/fixtures/fixapi/
^/a/([\w\.:-]+)/importer/excel/bulk_upload_api/$
^/a/([\w\.:-]+)/importer/excel/config/$
^/a/([\w\.:-]+)/messaging/broadcasts/add/$
^/a/([\w\.:-]+)/messaging/broadcasts/edit/([\w-]+)/([\w-]+)/$
^/a/([\w\.:-]+)/messaging/conditional/add/$
^/a/([\w\.:-]+)/messaging/conditional/edit/([\w-]+)/$
^/a/([\w\.:-]+)/receiver/$
^/a/([\w\.:-]+)/receiver/([\w-]+)/$
^/a/([\w\.:-]+)/receiver/api/$
^/a/([\w\.:-]+)/receiver/secure/$
^/a/([\w\.:-]+)/receiver/secure/([\w-]+)/$
^/a/([\w\.:-]+)/receiver/submission/?$
^/a/([\w\.:-]+)/reports/export/(case_list_explorer|duplicate_cases)/$
^/a/([\w\.:-]+)/settings/locations/import/$
^/a/([\w\.:-]+)/settings/locations/import/bulk_location_upload_api/$
^/a/([\w\.:-]+)/settings/project/basic/$
^/a/([\w\.:-]+)/settings/users/commcare/upload/$
^/a/([\w\.:-]+)/settings/users/commcare/upload/bulk_user_upload_api/$
^/a/([\w\.:-]+)/settings/users/join/([ \w-]+)/$
^/a/([\w\.:-]+)/settings/users/user_data/$
^/a/([\w\.:-]+)/settings/users/web/upload/$
^/formplayer/answer_media$
^/formplayer/new-form$
^/formplayer/validate_form$
^/gvi/api/sms/$
^/jserror/$
^/log_email_event/([\w]+)/([\w\.:-]+)/?$
^/log_email_event/([\w]+)/?$
^/telerivet/in/?$
^/telerivet/status/([\w\-]+)/$
""".strip().split('\n')

COMMCAREHQ_XML_QUERYSTRING_URLS_REGEX = r"""
^/trumpia/sms/([\w-]+)/?$
""".strip().split('\n')
