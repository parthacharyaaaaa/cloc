#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct {
    bool commentedBlock;
    bool validLine;
} ScanResult;

// Function to scan a line and determine if it contains code or comments
ScanResult scanLine(const char *line, int len, bool commentedBlock,
    const char *singleLineSymbol, int singleLineSymbolLength, 
    const char *multiLineStartSymbol, int multiLineStartSymbolLength, 
    const char *multiLineEndSymbol, int multiLineEndSymbolLength)
{
    ScanResult result;
    result.commentedBlock = commentedBlock;
    result.validLine = false;

    uint_fast16_t idx = 0;
    while(idx < len){
        /* Single line check */
        // Check for single-line comment
        if (singleLineSymbolLength > 0 && 
            (idx + singleLineSymbolLength <= len) &&
            strncmp(line + idx, singleLineSymbol, singleLineSymbolLength) == 0) {
            // Single comment symbol appears, anything after this is irrelevent
            break;
        }

        /* Multi line check */
        // Check for multiline comment start symbol
        if (multiLineStartSymbolLength > 0 &&
            (idx + multiLineStartSymbolLength <= len) &&
            strncmp(line + idx, multiLineStartSymbol, multiLineStartSymbolLength) == 0) {
            result.commentedBlock = true;
            idx += multiLineStartSymbolLength;
            continue;
        }

        // Check for multiline comment end symbol
        if (multiLineEndSymbolLength > 0 && 
            (idx + multiLineEndSymbolLength <= len) &&
            strncmp(line + idx, multiLineEndSymbol, multiLineEndSymbolLength) == 0) {
            result.commentedBlock = false;
            idx += multiLineEndSymbolLength;
            continue;
        }

        // Char found which was not in a comment, and is not a whitespace, newline, carriage feed, or tab.
        if (!(line[idx] == ' ' || line[idx] == '\t' || line[idx] == '\n' || line[idx] == '\r')) {
            result.validLine = true;
            idx++;
            continue;
        }
        idx++;
    }

    return result;
}