#!/usr/bin/python
# Written by Viet Le
# Date 27/05/2022
# Feel free to use for all purposes at your all risk

# The input file name should be a good backup config from the FortiGate and must contain 'config firewall service custom'

import re, os.path
import sys, getopt

# change the in/out file location here if runs from IDE
backup_file = 'in\\dummy-fw01_20220224_1800.conf'
# backup_file = 'D:\\Extracts\\vdom-address.conf'
output_folder = 'out\\vdom-services-output.csv'


def usage():
    """ Used to print Syntax
    """
    print("Syntax:\n\t{} -i <inputfile> -o <outputfile>".format(os.path.basename(__file__)))
    print("Examples:\n\t{} -i backup-config.conf -o results.csv".format(os.path.basename(__file__)))


def main(argv):
    global backup_file
    global output_folder

    try:
        opts, args = getopt.getopt(argv, "hi:o:", ["ifile=", "ofile="])
    except getopt.GetoptError:
        print("Error:\n\tInvalid commands")
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            usage()
            sys.exit()
        elif opt in ("-i", "--ifile"):
            backup_file = arg
        elif opt in ("-o", "--ofile"):
            output_file = arg


def get_vdoms(infile: str):
    """ Used to extract vdom list
            The backup config file should contain vdom list
        Parameters:
            infile (str): Input file contains FW policy only as input.
        Returns:
            vdom (list): List of vdom name.
    """
    try:
        with open(infile, 'r') as config_file:
            vdom_start = False
            vdom_stop = False
            vdom_list = ['root']
            for line in config_file:
                if re.findall(r'config vdom', line):
                    vdom_start = True
                elif re.findall(r'^end', line):
                    if vdom_start:
                        vdom_stop = True
                elif vdom_start and not vdom_stop:
                    if re.findall(r'edit\s.*', line):
                        vdom = line.strip('\n').strip(' ').split(' ')
                        vdom_name = vdom[1]
                        if vdom_name not in vdom_list:
                            vdom_list.append(vdom_name)
            return vdom_list

    except IOError as e:
        print("Input file error: {} or file {} is in used".format(e.strerror, infile))
        usage()
        sys.exit()


def get_columns(infile: str):
    """ Used to extract FW service objects list
        The backup config file must contain 'config firewall service custom' command.
    Parameters:
        infile (str): Input file contains FW service as input.
        vdom (str): takes vdom name
    Returns:
        columns (list): List of object name.
    """
    try:
        with open(infile, 'r') as config_file:
            start_table = False
            stop_table = False
            # column_name = ['id']
            column_name = ['vdom', 'name']
            for line in config_file:
                if re.findall(r'config firewall service custom[\r\n]', line):
                    start_table = True
                    stop_table = False
                elif re.findall(r'^end', line):
                    if start_table:
                        stop_table = True
                        start_table = False
                elif start_table and not stop_table:
                    if re.findall(r'set\s', line):
                        set_value = line.strip('\n').strip(' ').split(' ')
                        address_object = set_value[1]
                        if address_object not in column_name:
                            column_name.append(address_object)
            return column_name
    except IOError as e:
        print("Input file error: {} or file {} is in used".format(e.strerror, infile))
        usage()
        sys.exit()


if __name__ == "__main__":
    main(sys.argv[1:])

    print("Please wait! I am working on {}".format(backup_file))
    print('*' * 60)
    hit = 0  # count number of objects matched/exported
    start_table :bool = False
    rows = [' ']  # object place holder
    columns = get_columns(backup_file) # get the settings values

    rows *= len(columns)  # copy column structure, number max of column

    # Begin writing output header to output file, the outFile handle will remain opened until the end.
    try:
        outFile = open(output_folder, 'w')
        for field in columns:
            outFile.write(field + ',')
        outFile.write('\n')
    except IOError as e:
        print("Error: Cannot open Output file {} - {}".format(output_folder, e.strerror))
        usage()
        sys.exit()
    # End writing output header

    try:
        with open(backup_file, 'r') as config_file:
            start_table: bool = False
            current_vdom: str = 'root'
            for command_line in config_file:
                rows[0] = current_vdom  # root vdom always appear first
                if re.findall(r'^edit .*', command_line):
                    # start vdom config, will also include vdom definition at the beginning
                    # the next line will enter new vdom
                    current_vdom = command_line.strip(' ').strip('\n').split(' ')[1]
                    continue    # continue reading new config line

                if re.findall(r'config firewall service custom[\r\n]', command_line):
                    start_table = True
                elif re.findall(r'^end', command_line):
                    if start_table:
                        start_table = False
                elif start_table:  # and not end_of object table:
                    if re.findall(r'edit .*', command_line):
                        address_name = command_line.strip(' ')[5:]
                        rows[1] = address_name.strip('\n').strip('"')
                        hit += 1
                    elif re.findall(r'set\s', command_line):
                        value = command_line.strip('\n').strip(' ').split(' ')
                        object = value[1]
                        if object not in columns:  # hardly hit this conditions , just in case a field is missing
                            columns.append(object)
                            rows.append('')
                        idx = columns.index(object)  # find the index of field name in the column
                        options = ''  # contains all the values
                        for option in value[2:]:  # skip 'set object' and take the value only
                            options += option + ' '
                        rows[idx] = options.strip(' ')  # save value to the corresponding field
                    elif re.findall(r'next', command_line):  # end of table - flush to output file
                        for eachSetup in rows:
                            outFile.write(eachSetup + ',')
                        outFile.write('\n')
                        rows = [' ']  # reset the address place holder
                        rows *= len(columns)
    except IOError as e:
        print("Input file error: {} or file {} is in used".format(e.strerror, backup_file))
        usage()
        sys.exit()
    if hit > 0:
        print("Results: {} addresses exported to {}".format(hit, output_folder))
    else:
        print("There is no address in the input file {}".format(backup_file))
    outFile.close()
