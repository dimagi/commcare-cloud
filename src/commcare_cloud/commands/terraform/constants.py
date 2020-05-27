# Paste the output of the commcare-hq management command
#
#   ./manage.py list_waf_allow_patterns --compact
#
# to replace the contents of the multiline string
COMMCAREHQ_XML_POST_URLS_REGEX = r"""
^/a/([\w\.:-]+)/api/v([\d\.]+)/form/$|^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/app_logo/([\w\-]+)/$|^/a/([\w\.:-]+)/apps/([\w-]+)/multimedia/uploaded/image/$
^/a/([\w\.:-]+)/apps/edit_form_attr_api/([\w-]+)/([\w-]+)/([\w-]+)/$|^/a/([\w\.:-]+)/apps/patch_xform/([\w-]+)/([\w-]+)/$|^/a/([\w\.:-]+)/cloudcare/api/readable_questions/$
^/a/([\w\.:-]+)/data_dictionary/import$|^/a/([\w\.:-]+)/fixtures/edit_lookup_tables/upload/$|^/a/([\w\.:-]+)/fixtures/fixapi/|^/a/([\w\.:-]+)/importer/excel/bulk_upload_api/$
^/a/([\w\.:-]+)/receiver/$|^/a/([\w\.:-]+)/receiver/([\w-]+)/$|^/a/([\w\.:-]+)/receiver/secure/$|^/a/([\w\.:-]+)/receiver/secure/([\w-]+)/$|^/a/([\w\.:-]+)/receiver/submission/?$
^/formplayer/new-form$|^/formplayer/validate_form$|^/gvi/api/sms/$|^/jserror/$|^/telerivet/in/?$
""".strip().split()
