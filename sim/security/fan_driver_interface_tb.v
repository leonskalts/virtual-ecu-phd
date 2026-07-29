`timescale 1ns/1ps

module fan_driver_interface_tb (
    input  wire        clk,
    input  wire        reset_n,
    input  wire [15:0] fan_command,
    output wire [15:0] clean_fan_actual,
    output wire [15:0] trojan_fan_actual,
    output wire        trojan_triggered,
    output wire        payload_active,
    output wire [15:0] trigger_counter,
    output wire [15:0] trojan_clean_fan_command,
    output wire [15:0] trojan_debug_fan_actual
);
    fan_driver_interface_clean clean_dut (
        .clk(clk),
        .reset_n(reset_n),
        .fan_command(fan_command),
        .fan_actual(clean_fan_actual)
    );

    fan_driver_interface_trojan trojan_dut (
        .clk(clk),
        .reset_n(reset_n),
        .fan_command(fan_command),
        .fan_actual(trojan_fan_actual),
        .trojan_triggered(trojan_triggered),
        .payload_active(payload_active),
        .trigger_counter(trigger_counter),
        .clean_fan_command(trojan_clean_fan_command),
        .trojan_fan_actual(trojan_debug_fan_actual)
    );
endmodule
