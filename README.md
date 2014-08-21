So what I have in place is a rough guide, things have been peeled back into a more modular state. Makes things slightly more complicated, but it really extends to usability of it. 

Things of note:
1. Need to incorporate virtualenv awareness into existing supervisor and webworker role
2. Rolling updates are in place, but the webworker role itself is incomplete. I chose to focus on high level architecture
3. with the seperate regions, the hosts should simply be in seperate appropriate name inventories (us-production, us-staging, india-production, etc) which will allow for simplifying group names(webworker, proxy, etc)

