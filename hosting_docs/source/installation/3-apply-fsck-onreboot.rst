.. _cchq-manual-install:

applying file system check for every reboot 
====================================================

Checking the file system for errors is an important part of Linux system administration. It is a good troubleshooting 

step to perform when encountering bad performance on read and write times, or file system errors. 

This tutorial will walk you through the process on how to force fsck to perform a file system check on the next system reboot
 or force file system check for any desired number of system reboots on root mount point.

1. View and modify PASS value in /etc/fstab
----------------

First, use the blkid command to figure out the UUID value of the file system you want to check.

blkid /dev/sda3
/dev/sda3: UUID="c020d4d8-c104-4140-aafc-24f7f89f8629" BLOCK_SIZE="4096" TYPE="ext4" PARTUUID="22ada8f4-5222-4049-b0fe-a3274516754d"

Then, grep for that UUID in the /etc/fstab file.

$ grep c020d4d8-c104-4140-aafc-24f7f89f8629 /etc/fstab 
UUID=c020d4d8-c104-4140-aafc-24f7f89f8629 /               ext4    defaults 0       0


The last column that is a column 6, aka fsck PASS column is used by fsck to determine whether fsck should check filesystem before 
it is mounted and in which order given partitions in /etc/fstab should be checked. Possible entries for fstab PASS column are 0,1 and 2.

0 - disabled, that is do not check the filesystem.
1 - partition with this PASS value has a higher priority and is checked first. This value is usually set to root/partition.
2 - partitions with this PASS value will be checked last

change the value of last column to 1 and save exit

   eg. UUID=c020d4d8-c104-4140-aafc-24f7f89f8629 / ext4 defaults    0     1

Note: the above setting will apply a filesystem check on the root mount /


2. Change "Maximum number of mounts" 
----------------

To ensure that your file system is checked on the next reboot, we need to manipulate the filesystem’s 
“Maximum mount count” parameter. The following tune2fs command will ensure that filesystem /dev/sdX is 
checked every time your Linux system reboots. Please note that for this to happen the fsck’s PASS value in 
/etc/fstab must be set to a positive integer as discussed above.

sudo tune2fs -c 1 /dev/sdX

Note: /dev/sdX device where / is mounted

3. Fix Detected Errors Automatically during reboot
-----------------

 To try to fix potential problems without getting any prompts, pass the -y option to fsck.
 	eg. sudo fsck -y /dev/sda2

 This way, you say “yes, try to fix all detected errors” without being prompted every time. If no errors are found, 
 the output looks the same as without the -y option.

 So to apply this during reboot, without prompt, you have to Change kernel parameter. fsck.mode=force will force a file check.

 Steps:
~~~~~~~
 	1. open  /etc/default/grub 


 	2. add the following parameters fsck.mode=force fsck.repair=yes

 		::
         GRUB_CMDLINE_LINUX_DEFAULT="quiet splash fsck.mode=force fsck.repair=yes"

		the new parameter added here is fsck.mode=force fsck.repair=yes 


	caution: Make sure you don't edit anything else, and that the edits you've made are correct, or else your computer may fail to boot


	3. update grub configuration
		::
         sudo update-grub

