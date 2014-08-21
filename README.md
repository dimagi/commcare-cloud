So what I have in place is a rough guide, things have been peeled back into a more modular state. Makes things slightly more complicated, but it really extends to usability of it. 

Things of note:
1. webworker role needs work. I roughly reorganized it and put in some requirements, but I'm not familiar enough with django to be confident in configuration as such
2. Rolling updates are in place, but the webworker role itself is incomplete. I chose to focus on high level architecture
3. with the seperate regions, the hosts should simply be in seperate appropriate name inventories (us-production, us-staging, india-production, etc) which will allow for simplifying group names(webworker, proxy, etc). It'll also help simplify some jinja files(I'm looking at you roledefs.yml)
4. tagging tasks with their general purpose can be a great idea(setup, install, config), allowing you to limits what tasks happen in a playbook.
5. instead of tagging every task, you can use include statements to other plays, letting you split things up sensibly(like in the common roles splitting everything doing with users into a users.yml and including it in main.yml). It's a great way to stay organized!
6. Monolithicplaybooks should use the same include mechanic. Start your playbooks focused, then include them in a larger playbook if you want to do sitewide releases. There is no such thing as too many playbooks
