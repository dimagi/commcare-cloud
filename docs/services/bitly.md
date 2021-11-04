# Set up Bitly for generating app codes

To enable generating app shortcodes to install builds on CommCare mobile, you will need a [Bitly API key](https://app.bitly.com/settings/api/). 

You should add these in the ansible vault file as follows:

**vault.yml**
```yaml
localsettings_private:
  BITLY_OAUTH_TOKEN: ''
```
