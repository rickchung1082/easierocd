set detach-on-fork off
set target-async on
set pagination off
set non-stop on

file /usr/bin/python3
set args /home/scottt/work/easierocd/bin/easierocd-gdb

add-inferior -exec ./src/openocd
#break jim_target_reset
#break adapter_assert_reset

run
