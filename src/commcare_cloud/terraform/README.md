# Creating a new environment

In this example there's a root account for your AWS organization,
and the new environment will live in it's own linked account.

1. From the root account go to organizations and create a new account.
    - use an email like <mainaccount>+<env>@<org> 
2. Enter in new account email as if to log in and then go through the Forgot Password
   workflow to set password (to something randomized and strong). Save this password.
3. Log in using the new credentials.
4. Go to my credentials and enable the root account's access key.
   Copy these to your ~/.aws/credentials as
    ```
    [<org>-<env>]
    aws_access_key_id = "..."
    aws_secret_access_key = "..."
    ```
5. Add `aws_profile: <org>-<env>` to `terraform.yml` of your env.
6. Run `cchq <env> terraform init`
7. Run `cchq <env> terraform plan -target module.commcarehq.module.Users`
   and if the user list looks good...
8. Run `cchq <env> terraform apply -target module.commcarehq.module.Users`
   and respond `yes` when prompted.
9. In AWS console, go to IAM users and click on your own username.
10. Create access key and copy them to ~/.aws/credentials,
    replacing the root credentials you had there.
