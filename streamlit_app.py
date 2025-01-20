import re
import streamlit as st
import pandas as pd
import openpyxl
import tabula

def pdf_reader(pdf_file):
    dfs =[]
    tables = tabula.read_pdf(pdf_file, pages="all", multiple_tables=True, pandas_options={"header":None})

    # loop through each 
    for i, table in enumerate(tables):
        # This is to create a generic column name for each df instead of the first row of each table
        table.columns = [f"Col_{j+1}" for j in range(table.shape[1])]

        # reset index position
        table.reset_index(drop=True, inplace=True)
        
        dfs.append(table)
    
    return dfs

def gearbox_check():
    # ensure Col_1 exist and the df has enough variables
    if "Col_1" in dfs[0].columns and len(dfs[0]) > 1:
        index_1 = dfs[0]['Col_1'][1]

        # Check if the gearbox option is in index_1
        for item in gearbox_options:
            if item in index_1.split(): # splits the index_1 into multiple pieces
                return True
    return False # if it does not exist 

def sales_text():
    d = {
        "Specification":["Nominal Speed", "Nominal Torque", "Maximum Torque", "Version", 'Output Shaft Diameter',"Output Shaft Length"],
        "Value":[]
        }
    d["Value"] = [None] * len(d["Specification"])
    sales_text_df = pd.DataFrame(data=d)

    # d[0:2]
    first_three_index = [sales_text_df.loc[0, "Specification"],sales_text_df.loc[1, "Specification"],sales_text_df.loc[2, "Specification"]]

    for i, spec in enumerate(first_three_index):
        if not i == 2:
            matching_index = (dfs[1]["Col_1"] == spec).idxmax()
            sales_text_df.loc[i, "Value"] = dfs[1].loc[matching_index,"Col_2"]
        # some motors have the text "Maximum torque limted by gearbox" so for these I need to build a special structure
        elif i == 2:
            # Here I use Panda's .str function, that essentially loops through items inside the series for me and allows me to preform string operators i.e. slicing and lower()
            matching_index = (dfs[1]["Col_1"].str[:len("Maximum Torque")].str.lower() == spec.lower()).idxmax()
            sales_text_df.loc[i, "Value"] = dfs[1].loc[matching_index,"Col_2"]


    # Version index 3, will always be in dfs[-1]
    version_index = (dfs[-1]["Col_1"] == sales_text_df.loc[3, "Specification"]).idxmax()
    if version_index == 1:
        sales_text_df.loc[3, "Value"] = dfs[-1].loc[version_index, "Col_2"]
    else:
        sales_text_df.loc[3, "Value"] = 'NA'   

    if gearbox_check() == True:
        # index 4 & 5
        for i in range(4 ,6):
            gb_spec = sales_text_df.loc[i, "Specification"]
            for df in dfs:
                for j, row in df.iterrows():
                    if df.loc[j, "Col_1"] == sales_text_df.loc[i, "Specification"]: 
                        if gb_spec in df["Col_1"].values:
                            #gb_index = (df["Col_1"] == gb_spec).idxmax()
                            sales_text_df.loc[i, "Value"] = row['Col_2']
    elif not gearbox_check():
        for i in range(4,6):
            sales_text_df.loc[i, "Value"] = 'NA'

    
    return sales_text_df

def inkoop_text():
    d = {
        "Keys":["Motor","Gearbox","Brake","Encoder","Cover"],
        "Details":[None]
        }
    d["Details"] = [None] * len(d["Keys"])
    inkoop_text_df = pd.DataFrame(data=d)

    # Motor
    for df in dfs:
        for i in df.index:
            if df.loc[i, "Col_1"] == "Nominal Motor Voltage":
                motor_voltage = df.loc[i, "Col_2"]
                motor_voltage = motor_voltage.replace(" ","")
                break
            else:
                motor_voltage = False
        if motor_voltage:
            break
  
    inkoop_text_df.loc[0,"Details"] = dfs[0].loc[0,"Col_1"] + " " + motor_voltage
    

    # Gearbox
    if gearbox_check() == True:
        inkoop_text_df.loc[1,"Details"] = dfs[0].loc[1, "Col_1"]
    else:
        inkoop_text_df.loc[1,"Details"] = "NA"
    
    if gearbox_check() == True:
        gb_reducation = ""
        for df in dfs:
            # initially i was using enumerate but that is only for iterable items such as lists. For items inside of a df one must use .iterrows()
            # here i is still the index and then row is the content within the cells i.e. index , Col_1 , Col_2
            for i,row in df.iterrows():
                if row['Col_1'] == "Reduction":
                    # here, my loc returns a df, thus I need to use iloc as it returns based on the index which in this new df will be 0
                    gb_reducation = row['Col_2']
                    gb_match = re.search(r'=(.*)', gb_reducation)
                    if gb_match:
                        gb_reducation = gb_match.group(1).strip()
                        break
        
        inkoop_text_df.loc[1, "Details"] = f'{inkoop_text_df.loc[1, "Details"]} ({gb_reducation})'

    raw_attachment_list = []
    attachment_list = []

    if gearbox_check() == True and len(dfs[0]["Col_1"]) > 1:
        # Use range function more often, it is powerful
        for i in range(2, len(dfs[0]["Col_1"])):
            raw_attachment_list.append(dfs[0]['Col_1'][i])

    elif gearbox_check() == False and len(dfs[0]["Col_1"]) > 1:
        for i in range(1, len(dfs[0]["Col_1"])):
            raw_attachment_list.append(dfs[0]['Col_1'][i])
            
    for i in raw_attachment_list:
        item = i.split('+')
        # use extend instead of append. Append creates a [] within the initial [] but extend just well... extends
        attachment_list.extend(item)

    brake_found = False
    encoder_found = False

    for i,j in enumerate(attachment_list):
        if j in brake_options:
            inkoop_text_df.loc[2,"Details"] = attachment_list[i]
            brake_found = True
            continue
        elif j[:2] in encoder_options:
            inkoop_text_df.loc[3,"Details"] = attachment_list[i]
            encoder_found = True
            break

    if not brake_found:
        inkoop_text_df.loc[2,"Details"] = 'NA'

    if not encoder_found:
        inkoop_text_df.loc[3,"Details"] = 'NA'
          
    # Brake text 

    if brake_found:
        for df in dfs:
            if df.loc[0,"Col_1"] == "Attachment":
                for i,j in enumerate(df['Col_1']):
                    if df.loc[i,"Col_2"] == "Power off brake":
                        brake_type = 'R'
                        break
                    elif df.loc[i,"Col_2"] == "Power on brake":
                        brake_type = 'A'
                        break
                    else:
                        brake_type = 'NA'
                        
                inkoop_text_df.loc[inkoop_text_df['Keys'] == 'Brake', 'Details'] = inkoop_text_df.loc[inkoop_text_df['Keys'] == 'Brake', 'Details'] + brake_type

        # cover details
    cover_status = False
    for df in dfs:
        if df.loc[0,"Col_1"] == "Attachment":
            for i,j in enumerate(df['Col_1']):
                if df.loc[i, 'Col_1'] == "Protection Cover":
                    cover_status = df.loc[i,'Col_2']
                else:
                    cover_status = False

        for df in dfs:
            if df.loc[0,"Col_1"] == "Attachment":
                for i,j in enumerate(df['Col_1']):
                    if df.loc[i, 'Col_1'] == "Protection class":
                        protection_class = df.loc[i,'Col_2']
                        break
        
            if not cover_status:
                inkoop_text_df.loc[4,"Details"] = "NA"
            elif  cover_status == "Yes":
                inkoop_text_df.loc[4,"Details"] = protection_class
            else:
                inkoop_text_df.loc[4,"Details"] = "NA"

    # encoder details

    encoder_channel = False
    for df in dfs:
        if df.loc[0, "Col_1"] == "Attachment":
            for i,j in enumerate(df["Col_1"]):
                if df.loc[i,"Col_1"] == "Encoder Channels":
                    encoder_channel = df.loc[i, "Col_2"]
                    break
                else:
                    encoder_channel = False


    for df in dfs:
        if df.loc[0, "Col_1"] == "Attachment":
            for i,j in enumerate(df["Col_1"]):
                if df.loc[i,"Col_1"] == "Encoder Resolution":
                    encoder_resolution = df.loc[i, "Col_2"]
                    e_stop_sign = encoder_resolution.find('p')
                    encoder_resolution = encoder_resolution[:e_stop_sign-1]
                    break
                else:
                    encoder_resolution = False

    for df in dfs:
        if df.loc[0, "Col_1"] == "Attachment":
            for i,j in enumerate(df["Col_1"]):
                if df.loc[i,"Col_1"] == "Encoder supply Voltage":
                    encoder_volt = df.loc[i, "Col_2"]+"V"
                    break
                else:
                    encoder_volt = False

    encoder_text_p1 = ""
    encoder_text_p2 = ""


    if encoder_channel:
        encoder_text = str(inkoop_text_df.loc[3, "Details"])

        # using re, match the data pattern 
        pattern =  re.match(r"(\D*)(\d+)(\D*)", encoder_text)

        if pattern:
            encoder_text_p1 = pattern.group(1) + pattern.group(2)
            encoder_text_p2 = pattern.group(3)
            
        else:
            encoder_text_p1 = encoder_text

    if not encoder_channel:
        inkoop_text_df.loc[3, "Details"] = "NA"
    elif not str(encoder_text_p2) == "":
        inkoop_text_df.loc[3, "Details"] = encoder_text_p1 + f'-{encoder_channel}-{encoder_resolution.strip()} {encoder_text_p2} {encoder_volt}'
    else:
        inkoop_text_df.loc[3, "Details"] = encoder_text_p1 + f'-{encoder_channel}-{encoder_resolution.strip()} {encoder_volt}'


    return inkoop_text_df

def description_1():
    if gearbox_check():
        return f"{inkoop_text_df.loc[0, 'Details']} + {inkoop_text_df.loc[1, 'Details']}"
    else:
        return f"{inkoop_text_df.loc[0, 'Details']}"

def description_2():
    description_parts = []
    for i in range(2, 5):
        detail = inkoop_text_df.loc[i, "Details"]
        if detail != "NA":
            description_parts.append(detail) 
    
    return ' + '.join(description_parts)

# pdf_path = r'/Users/dawid/Desktop/Documents/Currnet Job/ERIKS/Projects/Dunker PDF Reader/29811731.pdf'
# all available gearbox types
gearbox_options = ['PLG','KG','SG','STG','NG']

# Attachment options
brake_options = ["E22","E38","E90", 'E100', 'E310','E600']

encoder_options = ['RE','MG','MR','ME','AE']

st.title("Dunker PDF Reader")

uploaded_file = st.file_uploader("Upload your pdf")

if uploaded_file:
    try:

        dfs = pdf_reader(uploaded_file)

        sales_text_df = sales_text()
        sales_text_df

        inkoop_text_df = inkoop_text()
        inkoop_text_df

        description_one = description_1()
        description_two = description_2()

        print(description_1)
        print(description_2)
    except Exception as e:
        st.error(f"An error occured while processing file {e}")

else:
    st.info("Please upload the PDF file") 
