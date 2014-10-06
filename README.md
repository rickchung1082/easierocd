= EasierOCD

Goal: make using popular hardware debuggers easy and support ARM Cortex-M microcontrollers well.

= Why OpenOCD is so Hard to Use

Initial hardware setup only works when you specify every choice correctly in an unfamiliar programming language that matches the OpenOCD version.
For software development, the smart way to use OpenOCD, to have one daemon per adapter running in the background as needed, is not the obvious way to use it.
When looking for new chip support, config files found on the Internet often only work with a specific OpenOCD version. It's hard to tell the required software version to get a specific hardware to work.

== Initial Hardware Setup

* No hardware adapter detection even though most are USB
* Must sepcify how the debug adapter is connected to the target, typicall SWD or JTAG or Single Wire etc (OpenOCD "transport layer")
	Good defaults can sometimes be guessed from the adapter, e.g. ST-Link/v2-1, CMSIS-DAP typically means SWD instead of JTAG
	The effects whether the nRESET signal is connected (OpenOCD "reset_config srst_only" etc)
* No target autodetection through JTAG and or SWD IDs
	For ARM Cortex CPUs, target SWD ID plus memory mapped registers can be used to detect the target CPU.
	From the target CPU ID we can consult the prebuilt table of meomry size, flash algorithms and other necessary per chip setup tasks like clock config and  

== Software Development

The easiest way to write to flash memory is by using the 'openocd' command but it conflicts with a gdbserver running in the background

* For software development, the smart way to use OpenOCD, to run one daemon per adapter as needed, is not the obvious way to use it.
	Need a way to start one daemon instance per debug adapter as needed
* For running one daemon per adapter, local TCP port numbers are not as easy to manage as Unix domain sockets or Windows named pipes
* ARM Cortex-M{3,4} SWV tracing is not well supported
	SWO tracing and specfically the SWV configuration should be an ARM level feature (like ETB)
	and should be suitable to serve as the basis for building sampling based profilers and system wakeup debuggers
	
	OpenOCD currently instead has ST-Link specific SWO support that has to be specified at the very beginning and can't be redirected to TCP or local domain sockets
	Search for "hla " in http://openocd.sourceforge.net/doc/html/Debug-Adapter-Configuration.html
	OpenOCD: hla trace SOURCE_CLOCK_HZ OUTPUT_FILE
* ARM Cortex-M0+ ETB tracing is not well supported
* ARM Semihosting (OpenOCD: arm_semihosting.c)
	search for "semihosting" http://openocd.sourceforge.net/doc/html/Architecture-and-Core-Commands.html
	OpenOCD: arm semihosting [enable|disable]
** I/O redirection through TCP ports or local sockets should be supported (OpenOCD just does getchar()/putchar())
** File sharing using a local folder as root should supported (OpenOCD just calls open(), remove())
** Report exception should support redirection (OpenOCD just prints to stderr)

== New Hardware Suppport

* You really want a device database annotated with user sucess or failture stories and the software version required
* Must google for success storis for whether flash writing or debugging works


= OpenOCD Strong Points

It's an established community focal point.

* For debug adapter support, members sometimes has access to documentation under NDA (e.g. ST-Link USB protocol)
	* OpenOCD community members have relationship with chip vendors like TI and ST.

* Collects per chip knowledge like flash algorithms, clock setup, boot mode (ISP etc), interrupt vector relocation etc
	Initial chips setup are typically expressed as TCL commmands that are launched by the OpenOCD reset hook
	"Flash algorithms" here are really programs that run on the target CPU that knows how to erase, read and write flash memory

= Other Topics

