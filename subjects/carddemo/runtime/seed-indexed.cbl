      ******************************************************************
      * Synthetic GnuCOBOL INDEXED/sequential seeder for CBTRN02C.
      * Uses the pinned CardDemo copybooks. Not IBM VSAM. Not CICS.
      * Not a legacy test suite. Values are fixture-only.
      ******************************************************************
       IDENTIFICATION DIVISION.
       PROGRAM-ID. SEEDIDX.
       ENVIRONMENT DIVISION.
       INPUT-OUTPUT SECTION.
       FILE-CONTROL.
           SELECT DALYTRAN-FILE ASSIGN TO DALYTRAN
                  ORGANIZATION IS SEQUENTIAL
                  ACCESS MODE  IS SEQUENTIAL
                  FILE STATUS  IS DALYTRAN-STATUS.
           SELECT XREF-FILE ASSIGN TO XREFFILE
                  ORGANIZATION IS INDEXED
                  ACCESS MODE  IS SEQUENTIAL
                  RECORD KEY   IS FD-XREF-CARD-NUM
                  FILE STATUS  IS XREFFILE-STATUS.
           SELECT ACCOUNT-FILE ASSIGN TO ACCTFILE
                  ORGANIZATION IS INDEXED
                  ACCESS MODE  IS SEQUENTIAL
                  RECORD KEY   IS FD-ACCT-ID
                  FILE STATUS  IS ACCTFILE-STATUS.
           SELECT TCATBAL-FILE ASSIGN TO TCATBALF
                  ORGANIZATION IS INDEXED
                  ACCESS MODE  IS SEQUENTIAL
                  RECORD KEY   IS FD-TRAN-CAT-KEY
                  FILE STATUS  IS TCATBALF-STATUS.
       DATA DIVISION.
       FILE SECTION.
       FD  DALYTRAN-FILE.
       01  FD-TRAN-RECORD               PIC X(350).
       FD  XREF-FILE.
       01  FD-XREFFILE-REC.
           05 FD-XREF-CARD-NUM          PIC X(16).
           05 FD-XREF-DATA              PIC X(34).
       FD  ACCOUNT-FILE.
       01  FD-ACCTFILE-REC.
           05 FD-ACCT-ID                PIC 9(11).
           05 FD-ACCT-DATA              PIC X(289).
       FD  TCATBAL-FILE.
       01  FD-TRAN-CAT-BAL-RECORD.
           05 FD-TRAN-CAT-KEY.
              10 FD-TRANCAT-ACCT-ID     PIC 9(11).
              10 FD-TRANCAT-TYPE-CD     PIC X(02).
              10 FD-TRANCAT-CD          PIC 9(04).
           05 FD-FD-TRAN-CAT-DATA       PIC X(33).
       WORKING-STORAGE SECTION.
       COPY CVTRA06Y.
       COPY CVACT03Y.
       COPY CVACT01Y.
       01  DALYTRAN-STATUS              PIC X(02).
       01  XREFFILE-STATUS              PIC X(02).
       01  ACCTFILE-STATUS              PIC X(02).
       01  TCATBALF-STATUS              PIC X(02).
       PROCEDURE DIVISION.
           PERFORM 1000-SEED-DALYTRAN
           PERFORM 2000-SEED-XREF
           PERFORM 3000-SEED-ACCOUNT
           PERFORM 4000-SEED-TCATBAL
           DISPLAY 'S3 SEEDIDX OK runtime=gnucobol-indexed-bdb-fixture'
           GOBACK.
       1000-SEED-DALYTRAN.
           OPEN OUTPUT DALYTRAN-FILE
           IF DALYTRAN-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL DALYTRAN open ' DALYTRAN-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           INITIALIZE DALYTRAN-RECORD
           MOVE 'SYNTH00000000001' TO DALYTRAN-ID
           MOVE '01' TO DALYTRAN-TYPE-CD
           MOVE 1 TO DALYTRAN-CAT-CD
           MOVE 'SYNTHETIC' TO DALYTRAN-SOURCE
           MOVE 'Synthetic fixture purchase' TO DALYTRAN-DESC
           MOVE 10.00 TO DALYTRAN-AMT
           MOVE 1 TO DALYTRAN-MERCHANT-ID
           MOVE 'Synthetic Merchant' TO DALYTRAN-MERCHANT-NAME
           MOVE 'Fixture City' TO DALYTRAN-MERCHANT-CITY
           MOVE '00000' TO DALYTRAN-MERCHANT-ZIP
           MOVE '4000000000000001' TO DALYTRAN-CARD-NUM
           MOVE '2024-06-01-10.00.00.000000' TO DALYTRAN-ORIG-TS
           WRITE FD-TRAN-RECORD FROM DALYTRAN-RECORD
           IF DALYTRAN-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL DALYTRAN write1 ' DALYTRAN-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           MOVE 'SYNTH00000000002' TO DALYTRAN-ID
           MOVE '4000000000009999' TO DALYTRAN-CARD-NUM
           WRITE FD-TRAN-RECORD FROM DALYTRAN-RECORD
           IF DALYTRAN-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL DALYTRAN write2 ' DALYTRAN-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           CLOSE DALYTRAN-FILE.
       2000-SEED-XREF.
           OPEN OUTPUT XREF-FILE
           IF XREFFILE-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL XREF open ' XREFFILE-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           INITIALIZE CARD-XREF-RECORD
           MOVE '4000000000000001' TO XREF-CARD-NUM
           MOVE 1 TO XREF-CUST-ID
           MOVE 1 TO XREF-ACCT-ID
           WRITE FD-XREFFILE-REC FROM CARD-XREF-RECORD
           IF XREFFILE-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL XREF write ' XREFFILE-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           CLOSE XREF-FILE.
       3000-SEED-ACCOUNT.
           OPEN OUTPUT ACCOUNT-FILE
           IF ACCTFILE-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL ACCT open ' ACCTFILE-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           INITIALIZE ACCOUNT-RECORD
           MOVE 1 TO ACCT-ID
           MOVE 'Y' TO ACCT-ACTIVE-STATUS
           MOVE 0 TO ACCT-CURR-BAL
           MOVE 99999.00 TO ACCT-CREDIT-LIMIT
           MOVE 99999.00 TO ACCT-CASH-CREDIT-LIMIT
           MOVE '2020-01-01' TO ACCT-OPEN-DATE
           MOVE '2099-12-31' TO ACCT-EXPIRAION-DATE
           MOVE '2099-12-31' TO ACCT-REISSUE-DATE
           MOVE 0 TO ACCT-CURR-CYC-CREDIT
           MOVE 0 TO ACCT-CURR-CYC-DEBIT
           MOVE '00000' TO ACCT-ADDR-ZIP
           MOVE 'SYNTHETIC' TO ACCT-GROUP-ID
           WRITE FD-ACCTFILE-REC FROM ACCOUNT-RECORD
           IF ACCTFILE-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL ACCT write ' ACCTFILE-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           CLOSE ACCOUNT-FILE.
       4000-SEED-TCATBAL.
           OPEN OUTPUT TCATBAL-FILE
           IF TCATBALF-STATUS NOT = '00'
              DISPLAY 'S3 SEEDIDX FAIL TCATBAL open ' TCATBALF-STATUS
              MOVE 12 TO RETURN-CODE
              GOBACK
           END-IF
           CLOSE TCATBAL-FILE.
       END PROGRAM SEEDIDX.
