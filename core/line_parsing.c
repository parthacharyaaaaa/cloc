#include <stdint.h>
#include <stdbool.h>
#include <string.h>

typedef struct {
    bool commentedBlock;
    int validLines;
} BatchScanResult;

BatchScanResult scanBatch(const char *lines[], int lineCount, bool commentedBlock, int minChars,
    const char *singleLineSymbol, int singleLineSymbolLength, 
    const char *multiLineStartSymbol, int multiLineStartSymbolLength, 
    const char *multiLineEndSymbol, int multiLineEndSymbolLength)
    {
        BatchScanResult result;
        result.commentedBlock = commentedBlock;
        result.validLines = 0;

        uint_fast16_t idx, validChars;
        size_t len;
        bool bSingleLineSymbolPreface;
        for(int i = 0; i < lineCount; i++){
            const char* line = lines[i];
            len = strlen(line);
            idx = 0;
            validChars = 0;

            // NOTE: In a language with multiline comments (Like C), a line like "// */" would still end a commented block,
            // even if it is prefixed by a single line comment symbol. However, a line like "// /*" would not begin a commented block.
            // Therefore, we unfortunately can only skip scanning at a single line comment if we are not currently in a commented block   
            bSingleLineSymbolPreface = false;

            while(idx < len){
                /* Single line check */
                // Check for single-line comment
                if (singleLineSymbolLength > 0 && 
                    (idx + singleLineSymbolLength <= len) &&
                    strncmp(line + idx, singleLineSymbol, singleLineSymbolLength) == 0) {
                    // Single comment symbol appears, characters that are NOT a multiline comment end symbol will be irrelevent now
                    idx+=singleLineSymbolLength;
                    if(!result.commentedBlock){
                        // Not in a multi line block, skip
                        break;
                    }
                    bSingleLineSymbolPreface = true;
                    continue;
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

                // Actual valid character, not prefaced by a single line comment symbol, and not inside a commented block
                if (!result.commentedBlock &&
                    !bSingleLineSymbolPreface &&
                    !(line[idx] == ' ' || line[idx] == '\t' || line[idx] == '\n' || line[idx] == '\r')) {
                    validChars++;
                }
                idx++;
            }
            // Finally, compare no. of valid characters with minChars to determine if this line should be counted as valid or no
            if (validChars > minChars){
                result.validLines++;
            }
        }

        return result;
    }