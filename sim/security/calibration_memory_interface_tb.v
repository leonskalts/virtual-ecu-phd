`timescale 1ns/1ps

module calibration_memory_interface_tb (
    input  wire               clk,
    input  wire               reset_n,
    input  wire signed [15:0] calibration_in,
    output wire signed [15:0] clean_calibration_out,
    output wire signed [15:0] trojan_calibration_out,
    output wire               trojan_triggered,
    output wire               payload_active,
    output wire [15:0]        trigger_counter,
    output wire signed [15:0] trojan_clean_calibration_value,
    output wire signed [15:0] trojan_debug_calibration_value
);
    calibration_memory_interface_clean clean_dut (
        .clk(clk),
        .reset_n(reset_n),
        .calibration_in(calibration_in),
        .calibration_out(clean_calibration_out)
    );

    calibration_memory_interface_trojan trojan_dut (
        .clk(clk),
        .reset_n(reset_n),
        .calibration_in(calibration_in),
        .calibration_out(trojan_calibration_out),
        .trojan_triggered(trojan_triggered),
        .payload_active(payload_active),
        .trigger_counter(trigger_counter),
        .clean_calibration_value(trojan_clean_calibration_value),
        .trojan_calibration_value(trojan_debug_calibration_value)
    );
endmodule
