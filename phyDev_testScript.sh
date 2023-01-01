#!/bin/bash
#test_log_filename="test_logs/"`date -u +%d%m%y%H%I%S`".log"
test_log_filename="test_logs/dummy.log"
#wpan-hwsim > "${test_log_filename}"
./.phyDev_testScript.py $test_log_filename $1
