`timescale 1ns/1ps

module calibration_memory_interface_clean #(
    parameter integer DATA_WIDTH = 16
) (
    input  wire                         clk,
    input  wire                         reset_n,
    input  wire signed [DATA_WIDTH-1:0] calibration_in,
    output reg  signed [DATA_WIDTH-1:0] calibration_out
);
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            calibration_out <= {DATA_WIDTH{1'b0}};
        else
            calibration_out <= calibration_in;
    end
endmodule
