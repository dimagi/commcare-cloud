# Creating a new environment

In this example there's a root account for your AWS organization,
and the new environment will live in it's own linked account.

1. From the root account go to My Organization and create a new account.
    - use an email like `<mainaccount>+<env>@<org>`
2. Enter in new account email as if to log in and then go through the Forgot Password
    workflow to set password (to something randomized and strong). Save this password.
3. Log in using the new credentials.
4. Go to My Security Credentials and enable the root account's access key.
    Copy these to your `~/.aws/credentials` as
    ```
    [<account_alias>]
    aws_access_key_id = "..."
    aws_secret_access_key = "..."
    ```
    and then also active MFA for your device.
5. Add `account_alias: <account_alias>` to `terraform.yml` of your env.
6. (If the S3 state bucket is under a different account) Go to https://console.aws.amazon.com/iam/home#/security_credential > Account Identifiers
    to get the Canonical User ID for the account, and then in an incognito tab log in
    under the account where the S3 state bucket lives, navigate to the S3 state bucket,
    and under Permissions > Access Control List > Access for other AWS accounts
    give your account access to the bucket using the Canonical User ID.
7. Run
    ```bash
    COMMCARE_CLOUD_DEFAULT_USERNAME=root cchq <env> aws-sign-in
    cchq <env> terraform init
    AWS_PROFILE=<account_alias>:session aws dlm create-default-role --region <region>
    cchq <env> terraform apply
    ```
9. In AWS console, go to IAM users and click on your own username.
10. Create access key and copy them to `~/.aws/credentials`,
    replacing the root credentials you had there.
11. In AWS console under My Security Credentials,
    delete the access key you originally made for the root user.
12. Log out of AWS and then log back in as your IAM user. (To give the account a memorable
    account alias, make sure to set `account_alias` in `terraform.yml`.)


## Give access to team members

Terraform will create an IAM user account for each user specified in `meta.yml`.
The accounts are created without access keys or the ability to log in,
so they are essentially "inactive" accounts.

To "activate" an account:
1. Go to IAM users and select the user.
2. Click on the Security Credentials tab. Next to "Console password" it should say "Disabled";
    click on the "Manage password" link next to that.
3. Next to "Console access" click "Enable"
4. Check the box next to "Require password reset"
5. If the person is next to you, let them type in a password from your keyboard;
    otherwise take note of the autogenerated password and send it to them securely.
6. Send them a link to `https://<account_alias>.signin.aws.amazon.com/console`
    and have them log in and reset their password.
7. Have them to go to My Security Credentials to create an access key
    and write it in their `~/.aws/credentials` under `[<account_alias>]`.


## First terraform run

You can run terraform with
```
cchq <env> terraform apply
```
