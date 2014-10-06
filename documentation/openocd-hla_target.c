struct target_type hla_target = {
	.name = "hla_target",
	.deprecated_name = "stm32_stlink",

	.init_target = adapter_init_target,
	.target_create = adapter_target_create,
	.examine = cortex_m_examine,
	.commands = adapter_command_handlers,

	.poll = adapter_poll,
	.arch_state = armv7m_arch_state,

	.target_request_data = hl_target_request_data,

	.halt = adapter_halt,
	.resume = adapter_resume,
	.step = adapter_step,

	.assert_reset = adapter_assert_reset,
	.deassert_reset = adapter_deassert_reset,

	.get_gdb_reg_list = armv7m_get_gdb_reg_list,

	.read_memory = adapter_read_memory,
	.write_memory = adapter_write_memory,
	.checksum_memory = armv7m_checksum_memory,
	.blank_check_memory = armv7m_blank_check_memory,

	.run_algorithm = armv7m_run_algorithm,
	.start_algorithm = armv7m_start_algorithm,
	.wait_algorithm = armv7m_wait_algorithm,

	.add_breakpoint = cortex_m_add_breakpoint,
	.remove_breakpoint = cortex_m_remove_breakpoint,
	.add_watchpoint = cortex_m_add_watchpoint,
	.remove_watchpoint = cortex_m_remove_watchpoint,
};
