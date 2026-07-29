`timescale 1ns/1ps

module coolant_sensor_interface_tb (
    input  wire               clk,
    input  wire               reset_n,
    input  wire signed [15:0] sensor_in,
    output wire signed [15:0] clean_sensor_out,
    output wire signed [15:0] trojan_sensor_out,
    output wire               trojan_triggered,
    output wire               payload_active,
    output wire [15:0]        trigger_counter,
    output wire signed [15:0] trojan_clean_sensor_value,
    output wire signed [15:0] trojan_debug_sensor_value
);

    coolant_sensor_interface_clean clean_dut (
        .clk(clk),
        .reset_n(reset_n),
        .sensor_in(sensor_in),
        .sensor_out(clean_sensor_out)
    );

    coolant_sensor_interface_trojan trojan_dut (
        .clk(clk),
        .reset_n(reset_n),
        .sensor_in(sensor_in),
        .sensor_out(trojan_sensor_out),
        .trojan_triggered(trojan_triggered),
        .payload_active(payload_active),
        .trigger_counter(trigger_counter),
        .clean_sensor_value(trojan_clean_sensor_value),
        .trojan_sensor_value(trojan_debug_sensor_value)
    );
endmodule
