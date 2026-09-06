      ******************************************************************
      * Harness stub for IBM Language Environment CEE3ABD.
      * This is not IBM LE. CBTRN02C CALL 'CEE3ABD' on I/O abend.
      * The stub displays an honest marker and returns 99.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. CEE3ABD.
       DATA DIVISION.
       LINKAGE SECTION.
       01  ABCODE                       PIC S9(9) BINARY.
       01  TIMING                       PIC S9(9) BINARY.
       PROCEDURE DIVISION USING ABCODE TIMING.
           DISPLAY 'S3 CEE3ABD STUB: not IBM Language Environment'
           DISPLAY 'S3 CEE3ABD STUB: abcode=' ABCODE ' timing=' TIMING
           MOVE 99 TO RETURN-CODE
           STOP RUN.
       END PROGRAM CEE3ABD.
