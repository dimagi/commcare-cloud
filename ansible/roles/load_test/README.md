First run
---------

* login to "load_test_runner" machine

  $ sudo -iu cchq
  $ cd pgbench-tools

* If you're starting a completely new set of tests that you don't want to compare to previous tests

  $ ./initialize
  
* create a new test set

  $ ./newset "initial test set"
  
* confirm the config is correct
  
  $ cat config
  
* run the tests

  $ ./runset
  

After making some changes e.g. db config
----------------------------------------

* create a new test set

  $ ./newset "initial test set"
  
* run the tests

  $ ./runset
  
  
Get the results
---------------

  $ tar -czvf results.tar.gz results/*
  
And then locally:
  
  $ scp {load_test_runner}:/home/cchq/pgbench-tools/results.tar.gz
