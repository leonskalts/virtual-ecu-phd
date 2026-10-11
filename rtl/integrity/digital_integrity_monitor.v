// Logical producer-owned boundary; one instance per sensor channel.
// CRC-32 is not authentication. Producer ports must be access-controlled externally.
module digital_integrity_monitor (
    input wire clk, reset,
    input wire publish, transform,
    input wire [31:0] producer_channel, producer_bits, producer_ms,
    input wire [31:0] consumer_channel, consumer_bits, consumer_sequence,
    input wire [31:0] consumer_ms, consumer_tag, delivered_bits, delivered_ms,
    output reg witness_valid,
    output reg [31:0] sealed_channel, sealed_bits, sealed_sequence,
    output reg [31:0] sealed_ms, sealed_tag,
    output wire [2:0] causes,
    output wire [1:0] result // 0 UNAVAILABLE, 1 PASS, 2 FAIL
);
    function [31:0] record_crc;
        input [31:0] channel, bits, sequence_number, timestamp;
        reg [127:0] payload;
        reg [31:0] crc;
        integer i;
        begin
            // Low bit first equals software's little-endian byte traversal.
            payload = {timestamp, sequence_number, bits, channel};
            crc = 32'hffffffff;
            for (i = 0; i < 128; i = i + 1)
                crc = (crc >> 1) ^ ((crc[0] ^ payload[i]) ? 32'hedb88320 : 32'b0);
            record_crc = ~crc;
        end
    endfunction

    wire [31:0] next_sequence = witness_valid ? sealed_sequence + 32'd1 : 32'd1;
    wire [31:0] new_tag = record_crc(publish ? producer_channel : sealed_channel,
        producer_bits, publish ? next_sequence : sealed_sequence,
        publish ? producer_ms : sealed_ms);
    always @(posedge clk) begin
        if (reset) begin
            witness_valid <= 1'b0;
            sealed_channel <= 0; sealed_bits <= 0; sealed_sequence <= 0;
            sealed_ms <= 0; sealed_tag <= 0;
        end else if (publish) begin
            witness_valid <= 1'b1;
            sealed_channel <= producer_channel;
            sealed_bits <= producer_bits;
            sealed_sequence <= next_sequence;
            sealed_ms <= producer_ms;
            sealed_tag <= new_tag;
        end else if (transform && witness_valid) begin
            // Trusted producer supplies result of its legitimate transformation.
            // Like di_transform: retain channel/sequence/time, update bits and tag.
            sealed_bits <= producer_bits;
            sealed_tag <= new_tag;
        end
    end
    assign causes[0] = witness_valid &&
        (delivered_bits != sealed_bits || consumer_bits != sealed_bits ||
         consumer_tag != sealed_tag || consumer_channel != sealed_channel);
    assign causes[1] = witness_valid &&
        (delivered_ms != sealed_ms || consumer_sequence != sealed_sequence || consumer_ms != sealed_ms);
    assign causes[2] = witness_valid &&
        (sealed_tag != record_crc(sealed_channel, sealed_bits, sealed_sequence, sealed_ms) ||
         consumer_tag != record_crc(consumer_channel, consumer_bits, consumer_sequence, consumer_ms));
    assign result = !witness_valid ? 2'd0 : (|causes ? 2'd2 : 2'd1);
endmodule
