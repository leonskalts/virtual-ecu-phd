`timescale 1ns/1ps

module fan_driver_interface_clean #(
    parameter integer DATA_WIDTH = 16
) (
    input  wire                  clk,
    input  wire                  reset_n,
    input  wire [DATA_WIDTH-1:0] fan_command,
    output reg  [DATA_WIDTH-1:0] fan_actual
);
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            fan_actual <= {DATA_WIDTH{1'b0}};
        else
            fan_actual <= fan_command;
    end
endmodule
