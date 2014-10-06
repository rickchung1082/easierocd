#0  hl_interface_init_target (t=0x8a6350) at hla_interface.c:69
        res = <optimized out>
        __func__ = "hl_interface_init_target"
        ii = <optimized out>
        limit = <optimized out>
        found = <optimized out>
#1  0x0000000000442f6b in run_command (num_words=1, words=0x8aa0c0, c=0x894d80, context=0x85f030) at command.c:613
        cmd = {ctx = 0x85f030, current = 0x894d80, name = 0x894de0 "init", argc = 0, argv = 0x8aa0c8}
        retval = <optimized out>
#2  script_command_run (interp=interp@entry=0x85f070, argc=<optimized out>, argv=argv@entry=0x7fffffffbe68, c=0x894d80, capture=<optimized out>) at command.c:210
        __func__ = "script_command_run"
        nwords = 1
        state = 0x8b4d10
        cmd_ctx = 0x85f030
#3  0x00000000004431bf in command_unknown (interp=0x85f070, argc=<optimized out>, argv=<optimized out>) at command.c:1016
        cmd_name = <optimized out>
        cmd_ctx = 0x85f030
        c = 0x894d80
        __func__ = "command_unknown"
        found = <optimized out>
        start = 0x7fffffffbe68
        count = <optimized out>
#4  0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=2, objv=objv@entry=0x7fffffffbe60) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x88cfc0
#5  0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8a6b50) at jim.c:10640
        argc = 2
        j = <optimized out>
        i = 3
        script = 0x8b4ef0
        token = 0x8a9ed0
        retcode = 0
        sargv = {0x8a72a0, 0x8a7590, 0x2, 0x5131d5 <Jim_ConcatObj+421>, 0x892300, 0x4, 0x85f070, 0x8aa060}
        argv = 0x7fffffffbe60
        prevScriptObj = 0x892180
#6  0x000000000051df35 in Jim_EvalCoreCommand (interp=0x85f070, argc=<optimized out>, argv=<optimized out>) at jim.c:12914
        rc = <optimized out>
#7  0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=3, objv=objv@entry=0x7fffffffbf80) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861350
#8  0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x892180) at jim.c:10640
        argc = 3
        j = <optimized out>
        i = 4
        script = 0x892380
        token = 0x8923b0
        retcode = 0
        sargv = {0x8922b0, 0x8a73d0, 0x8a72f0, 0x2, 0x85f070, 0x50f356 <Jim_FreeObj+54>, 0x8a6020, 0x8a6b50}
        argv = 0x7fffffffbf80
        prevScriptObj = 0x891ad0
#9  0x000000000051d4e0 in Jim_CatchCoreCommand (interp=0x85f070, argc=1, argv=0x7fffffffc108) at jim.c:13897
        exitCode = 0
        i = 1
        sig = 0
        ignore_mask = <optimized out>
#10 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=2, objv=objv@entry=0x7fffffffc100) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861c80
#11 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x891ad0) at jim.c:10640
        argc = 2
        j = <optimized out>
        i = 3
        script = 0x8913a0
        token = 0x892010
        retcode = 0
        sargv = {0x892110, 0x892180, 0x24, 0x1d, 0x571ec0, 0x1, 0x85f070, 0x50ffef <Jim_NewStringObjNoAlloc+15>}
        argv = 0x7fffffffc100
        prevScriptObj = 0x8914a0
#12 0x000000000051a7a3 in Jim_EvalExpression (interp=interp@entry=0x85f070, exprObjPtr=<optimized out>, exprResultPtrPtr=exprResultPtrPtr@entry=0x7fffffffc268) at jim.c:9395
        objPtr = 0x18
        staticStack = {0x7fffffffc228, 0xa00000005, 0xffffffffffffffff, 0xffffc238, 0x85f070, 0x8a6850, 0x8a74b0, 0x0, 0x32e19b8060 <_nl_global_locale>, 0x1c}
        i = 0
        retcode = 0
        e = {stack = 0x7fffffffc1c0, stacklen = 0, opcode = 32767, skip = 9070672}
#13 0x000000000051ab76 in Jim_GetBoolFromExpr (interp=interp@entry=0x85f070, exprObjPtr=<optimized out>, boolPtr=boolPtr@entry=0x7fffffffc2ac) at jim.c:9437
        retcode = <optimized out>
        wideValue = 0
        doubleValue = 4.3368291886911276e-317
        exprResultPtr = 0x50ce7f <JimStringCopyHTKeyCompare+15>
#14 0x000000000051e8d5 in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffc380) at jim.c:12034
        boolean = 0
        retval = <optimized out>
        current = 2
        falsebody = <optimized out>
#15 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffc380) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#16 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8914a0) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 6
        script = 0x890340
        token = 0x891bf0
        retcode = 0
        sargv = {0x891b20, 0x891d20, 0x891da0, 0x891e10, 0x891e80, 0x51abca <Jim_GetBoolFromExpr+106>, 0x8, 0x51196d <Jim_StringCompareObj+93>}
        argv = 0x7fffffffc380
        prevScriptObj = 0x890b40
#17 0x000000000051e9bf in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffc4f0) at jim.c:12046
        boolean = 1
        retval = <optimized out>
        current = 2
        falsebody = <optimized out>
#18 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffc4f0) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#19 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x890b40) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 6
        script = 0x890310
        token = 0x891790
        retcode = 0
        sargv = {0x891580, 0x891510, 0x8914a0, 0x8916d0, 0x8918c0, 0x51abca <Jim_GetBoolFromExpr+106>, 0x8a9f40, 0x8a9bb0}
        argv = 0x7fffffffc4f0
        prevScriptObj = 0x87eb70
#20 0x000000000051ea13 in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffc660) at jim.c:12057
        boolean = 0
        retval = <optimized out>
        current = 4
        falsebody = 3
#21 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffc660) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#22 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x87eb70) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 14
        script = 0x890370
        token = 0x8903a0
        retcode = 0
        sargv = {0x890970, 0x8909e0, 0x890a50, 0x890ad0, 0x890b40, 0x8a9db0, 0x85f070, 0x88f400}
        argv = 0x7fffffffc660
        prevScriptObj = 0x8a6650
#23 0x00000000005191bc in JimCallProcedure (interp=0x85f070, cmd=0x88f450, argc=3, argv=0x7fffffffc7e0) at jim.c:10878
        i = <optimized out>
        callFramePtr = 0x8a9ba0
        d = <optimized out>
        retcode = <optimized out>
        optargs = <optimized out>
        script = <optimized out>
        argv = 0x7fffffffc7e0
        argc = 3
        cmd = 0x88f450
        interp = 0x85f070
#24 0x0000000000519761 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=3, objv=objv@entry=0x7fffffffc7e0) at jim.c:10180
        retcode = <optimized out>
        cmdPtr = 0x88f450
#25 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8a6650) at jim.c:10640
        argc = 3
        j = <optimized out>
        i = 4
        script = 0x8a9950
        token = 0x8b4c60
        retcode = 0
        sargv = {0x8a6c40, 0x8a2cc0, 0x8a67c0, 0x5131d5 <Jim_ConcatObj+421>, 0x8a24a0, 0x4, 0x85f070, 0x8a99a0}
        argv = 0x7fffffffc7e0
        prevScriptObj = 0x899f50
#26 0x000000000051df35 in Jim_EvalCoreCommand (interp=0x85f070, argc=<optimized out>, argv=<optimized out>) at jim.c:12914
        rc = <optimized out>
#27 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=4, objv=objv@entry=0x7fffffffc900) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861350
#28 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x899f50) at jim.c:10640
        argc = 4
        j = <optimized out>
        i = 5
        script = 0x8a2880
        token = 0x8a5110
        retcode = 0
        sargv = {0x877760, 0x876ab0, 0x87bcd0, 0x8a6bf0, 0x0, 0x8a9b80, 0x85f070, 0x898f10}
        argv = 0x7fffffffc900
        prevScriptObj = 0x8a6970
#29 0x00000000005191bc in JimCallProcedure (interp=0x85f070, cmd=0x88ce60, argc=2, argv=0x7fffffffca80) at jim.c:10878
        i = <optimized out>
        callFramePtr = 0x8a3100
        d = <optimized out>
        retcode = <optimized out>
        optargs = <optimized out>
        script = <optimized out>
        argv = 0x7fffffffca80
        argc = 2
        cmd = 0x88ce60
        interp = 0x85f070
#30 0x0000000000519761 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=2, objv=objv@entry=0x7fffffffca80) at jim.c:10180
        retcode = <optimized out>
        cmdPtr = 0x88ce60
#31 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=scriptObjPtr@entry=0x8a6970) at jim.c:10640
        argc = 2
        j = <optimized out>
        i = 3
        script = 0x8a97c0
        token = 0x8a6d10
        retcode = 0
        sargv = {0x8a5ea0, 0x8a7360, 0x0, 0x892f70, 0x8, 0x32e167fd7c <malloc+92>, 0x8a9b60, 0xe}
        argv = 0x7fffffffca80
        prevScriptObj = 0x8a69c0
#32 0x000000000051b33b in Jim_EvalSource (interp=interp@entry=0x85f070, filename=filename@entry=0x0, lineno=lineno@entry=0, script=script@entry=0x5343c2 "transport init") at jim.c:10955
        retval = <optimized out>
        scriptObjPtr = 0x8a6970
#33 0x0000000000442cbf in command_run_line (context=<optimized out>, line=line@entry=0x5343c2 "transport init") at command.c:656
        retval = <optimized out>
        retcode = 0
        interp = 0x85f070
        __func__ = "command_run_line"
#34 0x0000000000405672 in handle_init_command (cmd=0x7fffffffccd0) at openocd.c:146
        retval = <optimized out>
        initialized = 1
        cmd = 0x7fffffffccd0
        retval = 0
        initialized = 1
#35 0x0000000000442f6b in run_command (num_words=1, words=0x8a6870, c=0x892f70, context=0x85f030) at command.c:613
        cmd = {ctx = 0x85f030, current = 0x892f70, name = 0x89c510 "init", argc = 0, argv = 0x8a6878}
        retval = <optimized out>
#36 script_command_run (interp=0x85f070, argc=<optimized out>, argv=<optimized out>, c=0x892f70, capture=<optimized out>) at command.c:210
        __func__ = "script_command_run"
        nwords = 1
        state = 0x8a96e0
        cmd_ctx = 0x85f030
#37 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=1, objv=objv@entry=0x7fffffffcdd0) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x893090
#38 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8a69c0) at jim.c:10640
        argc = 1
        j = <optimized out>
        i = 2
        script = 0x8a92a0
        token = 0x8a2b80
        retcode = 0
        sargv = {0x8a5390, 0x2, 0x2, 0x5131d5 <Jim_ConcatObj+421>, 0x892300, 0x8, 0x85f070, 0x8a6830}
        argv = 0x7fffffffcdd0
        prevScriptObj = 0x892180
#39 0x000000000051df35 in Jim_EvalCoreCommand (interp=0x85f070, argc=<optimized out>, argv=<optimized out>) at jim.c:12914
        rc = <optimized out>
#40 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=3, objv=objv@entry=0x7fffffffcef0) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861350
#41 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x892180) at jim.c:10640
        argc = 3
        j = <optimized out>
        i = 4
        script = 0x892380
        token = 0x8923b0
        retcode = 0
        sargv = {0x8922b0, 0x8a6b00, 0x8a6ab0, 0x2, 0x85f070, 0x50f356 <Jim_FreeObj+54>, 0x8a6b50, 0x8a69c0}
        argv = 0x7fffffffcef0
        prevScriptObj = 0x891ad0
#42 0x000000000051d4e0 in Jim_CatchCoreCommand (interp=0x85f070, argc=1, argv=0x7fffffffd078) at jim.c:13897
        exitCode = 0
        i = 1
        sig = 0
        ignore_mask = <optimized out>
#43 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=2, objv=objv@entry=0x7fffffffd070) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861c80
#44 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x891ad0) at jim.c:10640
        argc = 2
        j = <optimized out>
        i = 3
        script = 0x8913a0
        token = 0x892010
        retcode = 0
        sargv = {0x892110, 0x892180, 0x24, 0x1d, 0x571ec0, 0x1, 0x85f070, 0x50ffef <Jim_NewStringObjNoAlloc+15>}
        argv = 0x7fffffffd070
        prevScriptObj = 0x8914a0
#45 0x000000000051a7a3 in Jim_EvalExpression (interp=interp@entry=0x85f070, exprObjPtr=<optimized out>, exprResultPtrPtr=exprResultPtrPtr@entry=0x7fffffffd1d8) at jim.c:9395
        objPtr = 0x18
        staticStack = {0x7fffffffd198, 0xa00000005, 0xffffffffffffffff, 0xffffd1a8, 0x85f070, 0x8a67a0, 0x8a2940, 0x0, 0x32e19b8060 <_nl_global_locale>, 0x1c}
        i = 0
        retcode = 0
        e = {stack = 0x7fffffffd130, stacklen = 0, opcode = 32767, skip = 9070496}
#46 0x000000000051ab76 in Jim_GetBoolFromExpr (interp=interp@entry=0x85f070, exprObjPtr=<optimized out>, boolPtr=boolPtr@entry=0x7fffffffd21c) at jim.c:9437
        retcode = <optimized out>
        wideValue = 0
        doubleValue = 4.3368291886911276e-317
        exprResultPtr = 0x50ce7f <JimStringCopyHTKeyCompare+15>
#47 0x000000000051e8d5 in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffd2f0) at jim.c:12034
        boolean = 0
        retval = <optimized out>
        current = 2
        falsebody = <optimized out>
#48 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffd2f0) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#49 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8914a0) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 6
        script = 0x890340
        token = 0x891bf0
        retcode = 0
        sargv = {0x891b20, 0x891d20, 0x891da0, 0x891e10, 0x891e80, 0x51abca <Jim_GetBoolFromExpr+106>, 0x8, 0x51196d <Jim_StringCompareObj+93>}
        argv = 0x7fffffffd2f0
        prevScriptObj = 0x890b40
#50 0x000000000051e9bf in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffd460) at jim.c:12046
        boolean = 1
        retval = <optimized out>
        current = 2
        falsebody = <optimized out>
#51 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffd460) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#52 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x890b40) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 6
        script = 0x890310
        token = 0x891790
        retcode = 0
        sargv = {0x891580, 0x891510, 0x8914a0, 0x8916d0, 0x8918c0, 0x51abca <Jim_GetBoolFromExpr+106>, 0x8a7810, 0x880680}
        argv = 0x7fffffffd460
        prevScriptObj = 0x87eb70
#53 0x000000000051ea13 in Jim_IfCoreCommand (interp=0x85f070, argc=5, argv=0x7fffffffd5d0) at jim.c:12057
        boolean = 0
        retval = <optimized out>
        current = 4
        falsebody = 3
#54 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=5, objv=objv@entry=0x7fffffffd5d0) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x860aa0
#55 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x87eb70) at jim.c:10640
        argc = 5
        j = <optimized out>
        i = 14
        script = 0x890370
        token = 0x8903a0
        retcode = 0
        sargv = {0x890970, 0x8909e0, 0x890a50, 0x890ad0, 0x890b40, 0x8a34a0, 0x85f070, 0x88f400}
        argv = 0x7fffffffd5d0
        prevScriptObj = 0x8704c0
#56 0x00000000005191bc in JimCallProcedure (interp=0x85f070, cmd=0x88f450, argc=2, argv=0x7fffffffd750) at jim.c:10878
        i = <optimized out>
        callFramePtr = 0x880670
        d = <optimized out>
        retcode = <optimized out>
        optargs = <optimized out>
        script = <optimized out>
        argv = 0x7fffffffd750
        argc = 2
        cmd = 0x88f450
        interp = 0x85f070
#57 0x0000000000519761 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=2, objv=objv@entry=0x7fffffffd750) at jim.c:10180
        retcode = <optimized out>
        cmdPtr = 0x88f450
#58 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x8704c0) at jim.c:10640
        argc = 2
        j = <optimized out>
        i = 3
        script = 0x8a2ac0
        token = 0x8a6c90
        retcode = 0
        sargv = {0x8a4a20, 0x8a6a10, 0x3, 0x5131d5 <Jim_ConcatObj+421>, 0x89ce40, 0x4, 0x85f070, 0x8a36c0}
        argv = 0x7fffffffd750
        prevScriptObj = 0x89c450
#59 0x000000000051df35 in Jim_EvalCoreCommand (interp=0x85f070, argc=<optimized out>, argv=<optimized out>) at jim.c:12914
        rc = <optimized out>
#60 0x0000000000519728 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=4, objv=objv@entry=0x7fffffffd870) at jim.c:10184
        retcode = <optimized out>
        cmdPtr = 0x861350
#61 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=0x89c450) at jim.c:10640
        argc = 4
        j = <optimized out>
        i = 5
        script = 0x8a32e0
        token = 0x8a6ef0
        retcode = 0
        sargv = {0x877670, 0x89fc80, 0x89fcf0, 0x8a5e50, 0x0, 0x8a9a30, 0x85f070, 0x89cb00}
        argv = 0x7fffffffd870
        prevScriptObj = 0x87ff90
#62 0x00000000005191bc in JimCallProcedure (interp=0x85f070, cmd=0x8931a0, argc=1, argv=0x7fffffffd9f0) at jim.c:10878
        i = <optimized out>
        callFramePtr = 0x87d770
        d = <optimized out>
        retcode = <optimized out>
        optargs = <optimized out>
        script = <optimized out>
        argv = 0x7fffffffd9f0
        argc = 1
        cmd = 0x8931a0
        interp = 0x85f070
#63 0x0000000000519761 in JimInvokeCommand (interp=interp@entry=0x85f070, objc=objc@entry=1, objv=objv@entry=0x7fffffffd9f0) at jim.c:10180
        retcode = <optimized out>
        cmdPtr = 0x8931a0
#64 0x000000000051a1ab in Jim_EvalObj (interp=interp@entry=0x85f070, scriptObjPtr=scriptObjPtr@entry=0x87ff90) at jim.c:10640
        argc = 1
        j = <optimized out>
        i = 2
        script = 0x8a1ad0
        token = 0x8a68f0
        retcode = 0
        sargv = {0x8775d0, 0x5461b0, 0x0, 0x0, 0x0, 0x32e167fd7c <malloc+92>, 0x8a3310, 0x4}
        argv = 0x7fffffffd9f0
        prevScriptObj = 0x85f4c0
#65 0x000000000051b33b in Jim_EvalSource (interp=interp@entry=0x85f070, filename=filename@entry=0x0, lineno=lineno@entry=0, script=script@entry=0x5461b0 "init") at jim.c:10955
        retval = <optimized out>
        scriptObjPtr = 0x87ff90
#66 0x0000000000442cbf in command_run_line (context=context@entry=0x85f030, line=line@entry=0x5461b0 "init") at command.c:656
        retval = <optimized out>
        retcode = 0
        interp = 0x85f070
        __func__ = "command_run_line"
#67 0x0000000000405ac9 in openocd_thread (cmd_ctx=0x85f030, argv=0x7fffffffdcf8, argc=<optimized out>) at openocd.c:294
        ret = <optimized out>
#68 openocd_main (argc=<optimized out>, argv=0x7fffffffdcf8) at openocd.c:332
        cmd_ctx = 0x85f030
        __func__ = "openocd_main"
#69 0x00000032e1621d65 in __libc_start_main () from /lib64/libc.so.6
No symbol table info available.
#70 0x00000000004054c5 in _start ()
No symbol table info available.
