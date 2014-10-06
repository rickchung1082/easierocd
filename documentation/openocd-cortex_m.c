struct target_type cortexm_target = {
	.name = "cortex_m",
	.deprecated_name = "cortex_m3",

	.init_target = cortex_m_init_target,
	.target_create = cortex_m_target_create,
	.examine = cortex_m_examine,
	.commands = cortex_m_command_handlers,

	.poll = cortex_m_poll,
	.arch_state = armv7m_arch_state,

	.target_request_data = cortex_m_target_request_data,

	.halt = cortex_m_halt,
	.resume = cortex_m_resume,
	.step = cortex_m_step,

	.assert_reset = cortex_m_assert_reset,
	.deassert_reset = cortex_m_deassert_reset,
	.soft_reset_halt = cortex_m_soft_reset_halt,

	.get_gdb_reg_list = armv7m_get_gdb_reg_list,

	.read_memory = cortex_m_read_memory,
	.write_memory = cortex_m_write_memory,
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
