#!/usr/bin/python
###########################################################################################
# members -- class pulls in individual memberships for later processing
#
#       Date            Author          Reason
#       ----            ------          ------
#       04/11/15        Lou King        Create
#
#   Copyright 2015 Lou King
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#
###########################################################################################

# standard
import pdb
import argparse
import csv
from datetime import datetime

# home grown
from loutilities import timeu
ymd = timeu.asctime('%Y-%m-%d')
import version

########################################################################
class RunningAheadMembers():
########################################################################
    '''
    Collect member data from RunningAHEAD individual membership export
    file, containing records from the beginning of the club's member
    registration until present.

    Provide access functions to gain access to these membership records.

    :param memberfile: member filename, filehandle or string of file records
    :param overlapfile: debug file to test for overlaps between records
    '''

    #----------------------------------------------------------------------
    def __init__(self,memberfile,overlapfile=None):
    #----------------------------------------------------------------------

        # check for type of memberfile, assume not opened here
        openedhere = False

        # if str, assume this is the filename
        if type(memberfile) == str:
            memberfileh = open(memberfile, 'rb')
            openedhere = True

        # if file, remember handle
        elif type(memberfile) == file:
            memberfileh = memberfile

        # if list, it works like a handle
        elif type(memberfile) == list:
            memberfileh = memberfile

        # otherwise, not handled
        else:
            raise unsupportedFileType

        # input is csv file
        INCSV = csv.DictReader(memberfileh)
        
        ## preprocess file to remove overlaps between join date and expiration date across records
        # each member's records are appended to a list of records in dict keyed by (lname,fname,dob)
        self.names = {}
        for membership in INCSV:
            asc_joindate = membership['JoinDate']
            asc_expdate = membership['ExpirationDate']
            fname = membership['GivenName']
            lname = membership['FamilyName']
            dob = membership['DOB']
            memberid = membership['MemberID']
            fullname = '{}, {}'.format(lname,fname)

            # get list of records associated with each member, pulling out significant fields
            thisrec = {'MemberID':memberid,'name':fullname,'join':asc_joindate,'expiration':asc_expdate,'dob':dob,'fullrec':membership}
            thisname = (lname,fname,dob)
            if not thisname in self.names:
                self.names[thisname] = []
            self.names[thisname].append(thisrec)

        #debug
        if overlapfile:
            _OVRLP = open(overlapfile,'wb')
            OVRLP = csv.DictWriter(_OVRLP,['MemberID','name','dob','renewal','join','expiration','tossed'],extrasaction='ignore')
            OVRLP.writeheader()

        # sort list of records under each name, and remove overlaps between records
        for thisname in self.names:
            # sort should result so records within a name are by join date within expiration year
            # see http://stackoverflow.com/questions/72899/how-do-i-sort-a-list-of-dictionaries-by-values-of-the-dictionary-in-python
            self.names[thisname] = sorted(self.names[thisname],key=lambda k: (k['expiration'],k['join']))
            toss = []
            for i in range(1,len(self.names[thisname])):
                # if overlapped record detected, push this record's join date after last record's expiration
                # note this only works for overlaps across two records -- if overlaps occur across three or more records that isn't detected
                # this seems ok as only two record problems have been seen so far
                if self.names[thisname][i]['join'] <= self.names[thisname][i-1]['expiration']:
                    lastexp_dt = ymd.asc2dt(self.names[thisname][i-1]['expiration'])
                    thisexp_dt = ymd.asc2dt(self.names[thisname][i]['expiration'])
                    jan1_dt = datetime(lastexp_dt.year+1,1,1)
                    jan1_asc = ymd.dt2asc(jan1_dt)
            
                    # ignore weird record anomalies where this record duration is fully within last record's
                    if jan1_dt > thisexp_dt:
                        toss.append(i)
                        self.names[thisname][i]['tossed'] = 'Y'
            
                    # debug
                    if overlapfile:
                        OVRLP.writerow(self.names[thisname][i-1])    # this could get written multiple times, I suppose
                        OVRLP.writerow(self.names[thisname][i])
            
                    # update this record's join dates
                    self.names[thisname][i]['join'] = jan1_asc
                    self.names[thisname][i]['fullrec']['JoinDate'] = jan1_asc
            
            # throw out anomalous records. reverse toss first so the pops don't change the indexes.
            toss.reverse()
            for i in toss:
                self.names[thisname].pop(i)

        # close the debug file if present
        if overlapfile:
            _OVRLP.close()

        # close the file if opened here
        if openedhere:
            memberfileh.close()

    #----------------------------------------------------------------------
    def membership_iter(self):
    #----------------------------------------------------------------------
        '''
        generator function that yields full record for each memberships
        '''
        for thisname in self.names:
            for thismembership in self.names[thisname]:
                yield thismembership['fullrec']

    #----------------------------------------------------------------------
    def name_iter(self):
    #----------------------------------------------------------------------
        '''
        generator function that yields latest membership record for each names with
        JoinDate updated to earliest JoinDate
        '''
        for thisname in self.names:
            thismembership = self.names[thisname][-1]['fullrec']
            thismembership['JoinDate'] = self.names[thisname][0]['join']
            yield thismembership
