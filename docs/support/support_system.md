# Support System
## Why set up a Support System
CommCare is a powerful technology that caters to programs of different nature from simple data collection from a few hundred users to large scale deployment of millions of users. As with any technology, users using CommCare will need support beyond the user documentation to be successful at their job. To this extent, setting up a robust support system becomes essential for the success of any project in which CommCare is set.

### Identifying stakeholders
Projects using CommCare often have stakeholders who use and interact with CommCareHQ in different ways and they often have varied levels of technical expertise. Some examples of the stakeholders are community health / frontline workers (CHWs / FLWs), supervisors who monitor the FLWs, Monitoring and Evaluation (M&E) staff and data teams that deal with the data analytics and reporting side of the program, project team that is managing the CommCareHQ project setup and high level program staff. These users interact with CommCare mobile and server in different ways and will need different types of support.

Below are some example support issues that might come up from various stakeholders of the program
- An FLW not being able to sync or submit data to CommCareHQ server
- A project team member not seeing upto data on system

When setting up a support system we recommend you to do an exercise of identifying the stakeholders in your program and think through the program/technical workflows that these stakeholders would be part of and the potential issues that they might encounter.

## Components of a Support System
A good support system should have the following components:
- Training and documentation with common support questions and issues for end users
- Support channels for users to get the support they need
- Support team members
- Support processes and tools to track, triage, troubleshoot and escalate incoming issues

Below we give details on each component.

### Training and Documentation
A major portion of support issues end up being simply queries from users who may not know how to perform an action. The best way to avoid these is by providing training at the time of onboarding the users and documentation on how to use the system. <Todo; link to example collateral docs>

The documentation should also contain common queries that users might have. The support process should allow for these docs to be continuously updated as new repeating support queries are raised. 

### Support Channels for users to get the support they need
Support channels are required to enable communication between the end users facing an issue and the support team who have the expertise to resolve the issues. There are various possible support channels depending on how the support process is set up.
- Report an Issue from CommCare app. For this,
  * An FLW/CHW should be trained to use ‘Report an Issue’ in the CommCare mobile. 
  * When not able to use the app CHW/FLW should have an offline mechanism of reporting issues to supervisors or higher level program staff for support.
- ‘Report an Issue’ button on CommCareHQ Server
- Support Email: Higher level program staff should have access to a Direct support email address that auto creates tickets in a helpdesk app.
- An issue tracker CommCare application that has ‘Raise an Issue’ module which tracks the issues for all FLWs for supervisor’s reference

<p align="center">
    <img src="support_team.jpg" alt="Support team" style="width:75%" />
</p>

These channels are suitable for different stakeholders of the program depending on the level of their expertise in being able to communicate online. For example, a frontline worker may not be able to communicate via email with support in which case a direct phone support with a supervisor can be more easy. On the other hand if there are too many FLWs under a supervisor where a phone support is not possible, an Issue Tracker application could be useful.

### Support team
Support team could be a one or multi person team of experts who have a good overall understanding of the system and can troubleshoot and answer various issues coming from the users. The team should have direct access to developer team members who can troubleshoot issues that are beyond the scope of support team’s knowledge. The team will also need administrative level access to troubleshoot certain issues. The program and developer team should create policies to enable the support team without compromising on the security. The support team would also own the overall support process and improve it as necessary to achieve higher Service Level Agreements (SLAs).

### Support Processes
Support process is a defined process of how incoming support issues are handled from receiving the issues up till the resolution of these issues.

In its simplest form the support process might involve a developer answering all the issues from all the users of the system either via email or via phone by keeping track of these issues simply in an email or list of notes. This could work when the program is very small. This process would break down when the number of users increase even slightly. For programs of anything more than 20 FLWs we recommend a proper support process to handle and resolve all incoming issues in a timely manner.

Depending on the scale and complexity of the program either a basic or advanced process would become necessary. Below we describe the two processes in detail.

#### Basic Support Process and Tools
At a minimum, we recommend the below setup for handling support.
- Set up a helpdesk app such as Jira, Zendesk or other open source helpdesk app. Or if you are already using a project management software, you could use that instead.
- Set up a dedicated support email where all support queries can be sent to either via directly or via Report an Issue button on CommCareHQ. Configure this in your server using [support_email](https://github.com/dimagi/commcare-cloud/blob/master/environments/staging/public.yml#L53) param in your environment. 
- Integrate the helpdesk software with the support email such that all the incoming emails create individual tickets in the helpdesk software.
- Helpdesk software should have below fields
  * Title and Description of the issue
  * Status: To describe the status of the ticket such as incoming, waiting for user’s input, being worked on and resolved etc as you see fit
  * Assignee: This allows the ticket to be passed between various team members depending on their expertise.
  * Priority: This is a very important field. Please see below the section on priority
  * Any additional fields as you see fit for project management needs.
- Onboard various members of support, program and developer team members to the helpdesk app as necessary.

##### Priority field
A priority level such as P1, P2, P3, P4 etc that describes the urgentness of the ticket and the number of users it’s affecting. It’s good to have a team-wide common definition on what each priority level means and document it in a relevant place for everyone’s reference. Below is a suggested priority level based on Dimagi’s support process.
- **P1** : Severe (a blocker), don't do anything else. May have to sleep less tonight. There is (business loss) already. The longer it's not fixed, the longer the product and the team are in failure state. Examples: Site down, data loss, security breakdown etc.
- **P2** : A problem which has made an important/critical function unusable or unavailable and no workaround exists. Examples: All users not being able to sync with server.
- **P3** : High (Should be fixed), if not fixed, will lose integrity in product. Example: Pillows falling behind by a large backlog.
- **P4** : Normal (Should be fixed, time and resources permitting)
- **P5** : Low

The priority level helps the entire support team and developers to understand how they should prioritize the particular ticket. A support team member triaging the ticket can setup the priority.

##### Ticket Workflow
Once the support system is set up below is a general process that can be followed. Note that for P1/P2 we recommend a separate on-call like process stated here P1/P2 process recommendations <todo;link to P1/P2 process>.

<p align="center">
    <img src="local_hosting_support_workflow.png" alt="Local Hosting Support" style="width:90%" />
</p>

- An issue is reported view UI or directly
- A ticket is created in helpdesk app automatically or support creates it if the issue is reported via email/chat.
- When a new ticket arrives,
    * A support team member performs the initial investigation
    * If more information is required to resolve the issue the user is contacted for more information.
    * If the ticket fits P1/P2 criteria, follow P1/P2 process
    * Support team member updates the fields of the ticket such as priority, status and assignee.
    * Depending on the ticket, the support team member might resolve and respond back to the user or escalate it to a different team member from the program or developer team.
    * If the team is not able to get resolve, the ticket can be reported to Dimagi support directly if the team has a support plan or else to the public CommCare developers forum
    * If the ticket priority is low, the team might put it into a backlog that can be reviewed later.
- Once the resolution is found the support team member sends the resolution to the user and closes the ticket after updating relevant ticket fields.

Apart from this a regular periodical (weekly or biweekly) team calls could also be used to coordinate the overall support activities. 

##### P1/P2 Process
The standard support process stated above works well for tickets with priority lower than P2. As defined above tickets with priority P1 indicate a very urgent ticket that affects all users, which may be causing a downtime or irreversible data loss/corruption or other critical issues. P2 priority indicates a critical function being available that might soon result in a P1 issue if neglected. Given that there is a lot of urgency tied to P1 and P2, we recommend a separate process to resolve these issues.

The intention of a separate P1/P2 process is to address below unique expectations associated with  P1 or P2 incidents.
1. Fix the issue as soon as possible
2. Establish communication with users and stakeholders to inform about the issue
3. Followup Actions such as Root Cause Analysis to prevent issues like this from getting repeated

We recommend below a general process that addresses these three expectations. You may tweak it as you see fit in your organizational context or even create your own process but in the least it should address the above three expectations.

###### Process for P1/P2
1. Kickoff the process
    <ol>
        <li>Create a ticket and mark it’s priority to P1</li>
        <li>Form and gather an Incident Response Team consisting of a Developer lead who is the main developer to resolve the issue, a Response manager who makes sure the developer has all the resources to resolve the issue other strategic planning around the issue and Support lead to handles communication with external users and internal teams</li>
        <li>Do a P1 call with Incident Response Team members to troubleshoot and co-ordinate next steps on the issue. Create a shared live P1 document to add notes on the issue.</li>
        <li>Response manager or support lead announces the issue in the internal and external channels to let various stakeholders be informed about the issue. Various mechanisms exist to facilitate this</li>
            <ol>
                <li>Dedicated internal/external chat groups</li>
                <li>CommCareHQ Alerts Page (<>/alerts) has an alerts page where a new banner can be set up if the site is not down.</li>
                <li>Tools such as statuspage.io</li>
            </ol>    
   </ol>
2. Manage the issue
    <ol>
        <li>Response manager or support lead should periodically check in with the developer lead to understand the status and make sure the developer lead has all the support to resolve the issue in a timely manner.</li>
        <li>Post updates on the communication channels regarding the status and ETA.</li>
   </ol>
3. After the issue is resolved
    <ol>
        <li>Announce that the issue is resolved on various communication channels</li>
        <li>Take down any banners or update tools such as statuspage.io</li>
        <li>Change the priority of the ticket from P1 to other appropriate priority.</li>
        <li>Update the status of the ticket to ‘Pending Retro’</li>
   </ol>
4. Doing a Retrospective
    <ol>
        <li>Ask the developer lead to create a retrospective document that details the root cause of the issue and steps to be taken to prevent such issue from repeating in the future. The developer can use techniques such as <a href="https://en.wikipedia.org/wiki/Five_whys">Five Whys</a> to do the retrospective.</li>
        <li>Schedule a Retrospective meeting with a wider team to discuss the retrospective and do a postmortem analysis on the ticket to arrive at a comprehensive list of action items to prevent such issues from repeating and make process related improvements to minimize the resolution time.</li>
   </ol>

The main difference between a P1 and P2 issue is the urgency with which the issue needs to be resolved. The same process is recommended for P2 issues with relaxations in urgency which means it may not need as frequent and close monitoring as P1.

#### Advanced Support Process and Tools
Programs that are very large scale could produce a very high volume of support tickets that need to be resolved under SLAs. This requires more advanced support systems to be setup at multiple levels of the program in an escalating manner. This often needs to be planned as a core facet of the program from the ground up. A support system at this level usually consists of
- Issue Tracker Applications to supervisors to support FLWs
- Helpdesks at District/Block level and escalation process
- Program level support team at the top
- View into SLAs

There is no general setup that can be recommended to all the projects as each program has different needs at scale. Dimagi offers <todo; link to support system setup addon package> for this reason. If you require help setting up such system, please contact our delivery team to setup a support system for your project. 

## Support System Implementation checklist
As discussed above to implement a good support system all of the above components need to be in place. You can use the below checklist to make sure you have a robust support system in place.
1. Make sure enough training material and documentation exists for end users to prevent support queries.
2. Establish support channels with various stakeholders
3. Create a support team
4. Create documentation that outlines 
    <ol>
        <li>Definitions of various priorities</li>
        <li>The support processes for regular and P1/P2 tickets.</li>
    </ol>