from __future__ import annotations


def test_the_suite_renders_offscreen_agents_run_it_on_his_machine_where_each_widget_would_flash_a_window_set_by_default_so_a_developer_can_watch(qapp):
    assert qapp.platformName() == "offscreen"
