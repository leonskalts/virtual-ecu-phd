`timescale 1ns/1ps

module coolant_sensor_interface_clean #(
    parameter integer DATA_WIDTH = 16
) (
    input  wire                         clk,
    input  wire                         reset_n,
    input  wire signed [DATA_WIDTH-1:0] sensor_in,
    output reg  signed [DATA_WIDTH-1:0] sensor_out
);
    always @(posedge clk or negedge reset_n) begin
        if (!reset_n)
            sensor_out <= {DATA_WIDTH{1'b0}};
        else
            sensor_out <= sensor_in;
    end
endmodule
