'''
Created on Tue sep 20 2022
Contains the classes and functions to make the process interval objects

@author: Lucas Van der Hauwaert
email: lucas.vanderhauwaert@usc.es
'''

import os
import pandas as pd
import numpy as np
from collections import OrderedDict
from classes_intervals import InputIntervalClass, ReactorIntervalClass, OutputIntervalClass
from f_make_str_equations import  make_str_eq_smbl, make_str_eq_json
from f_usefull_functions import *
import json

# ============================================================================================================
# Validate the Excel file sheets, checks and error messages
# ============================================================================================================
"""
List of possible errors 
* make sure all separations are acounted for 
* make sure all names of the intervals are the same in each excel sheet 
* make sure the abbreviations of the output intervals are in the equations 
Write all error you encounter here 
Make sure only split, sep bool ands mix are the only words in the connection matrix 
make sure all abbreviations have a definition in the abbreviations sheet otherwise error
 """
def validate_seperation_coef(coef, intervalName, amountOfSep, connectionMatrix):
    coefList  = split_remove_spaces(coef, ';')
    arraysOfCoef = []
    for i in coefList:
        coefTuple = stringbounds_2_tuplebounds(i)
        coefArray = np.array(coefTuple)
        arraysOfCoef.append(coefArray)
    sumOfArrays = 0
    # check if there are as many separation processes as separation coefficient bounds
    if amountOfSep != len(arraysOfCoef):
        raise Exception("make sure all bounds are written for interval ".format(intervalName))
    # check if the sum of the separation coefficiets are one
    for i in arraysOfCoef:
        sumOfArrays += i
    nCol = np.shape(sumOfArrays)  #get the amount of columns
    if sum(sumOfArrays == np.ones(nCol)):
        pass
    else:
        raise Exception("the sum of the seperation coefficients for {} do not add up to 1, check the excel file".format(intervalName))

    # check if all the seperation processes are accounted for in the connenction matrix
    rowId = list(connectionMatrix['process_intervals']).index(intervalName)
    rowMatrix = connectionMatrix.iloc[rowId].drop(['process_intervals'])
    counterSeparation = 0
    counterSplit = 0
    for i in rowMatrix:
        if 'sep' in str(i):
            counterSeparation += 1
        if 'split' in str(i):
            counterSplit += 1

    if counterSeparation - counterSplit/2 != amountOfSep:
        raise Exception("Check interval {} there is a separation process missing in the connection matrix".format(intervalName))

def check_excel_file(excelName):
    loc = os.getcwd()
    posAlquimia = loc.find('Alquimia')
    loc = loc[0:posAlquimia+8]
    loc = loc + r'\excel files' + excelName

    DFIntervals = pd.read_excel(loc, sheet_name='input_output_intervals')
    DFReactors =  pd.read_excel(loc, sheet_name='reactor_intervals')
    DFConnectionMatrix = pd.read_excel(loc, sheet_name='connection_matrix')
    DFAbbr = pd.read_excel(loc, sheet_name='abbr')

    # check interval names in the connection matrix and interval list
    intervalNamesIn = remove_spaces(DFIntervals.process_intervals[DFIntervals.input_price != 0].to_list())
    intervalNamesReactors = remove_spaces(DFReactors['process_intervals'].to_list())
    intervalNamesOut = remove_spaces(DFIntervals.process_intervals[DFIntervals.output_price != 0].to_list())
    intervalNames = intervalNamesIn + intervalNamesReactors + intervalNamesOut

    intervalNamesConnenctionMatrixRow = remove_spaces(list(DFConnectionMatrix.columns))
    intervalNamesConnenctionMatrixRow.remove('process_intervals')
    intervalNamesConnenctionMatrixCol = remove_spaces(DFConnectionMatrix['process_intervals'].to_list())

    # check length
    if len(intervalNamesConnenctionMatrixCol) == len(intervalNamesConnenctionMatrixRow) == len(intervalNames):
        pass
    else:
        raise Exception('Interval name is missing in the connection matrix sheet or the interval sheet')
    # check names
    if intervalNames == intervalNamesConnenctionMatrixRow == intervalNamesConnenctionMatrixCol:
        pass
    else:
        positonError = [errorList for i, errorList in enumerate(intervalNames) if not intervalNames[i]
                                    == intervalNamesConnenctionMatrixRow[i] == intervalNamesConnenctionMatrixCol[i]]
        print(positonError)
        raise Exception('The names in the connection matrix sheet or the interval sheet are not the same')

    # check if all abbreviations are defined
    abbreviations = split_remove_spaces(list(DFReactors.inputs),',') \
                  + split_remove_spaces(list(DFReactors.outputs),',') \
                  + split_remove_spaces(list(DFIntervals.components),',')

    #uniqueListAbr = list(OrderedDict.fromkeys(abbreviations))
    abbrSet = set(abbreviations)
    abbrExcel = set(split_remove_spaces(list(DFAbbr.abbreviation),','))

    missingAbbr = abbrSet - abbrExcel
    if  missingAbbr:
        raise Exception('You are missing a definition for the following abbreviations: {}'.format(missingAbbr) )
    else:
        pass
# ============================================================================================================
# Functions to make the interval objects
# ============================================================================================================

# read function to automate making the interval classes
def make_input_intervals(excelName):
    loc = os.getcwd()
    posAlquimia = loc.find('Alquimia')
    loc = loc[0:posAlquimia+8]
    loc = loc + r'\excel files' + excelName

    DFIntervals = pd.read_excel(loc, sheet_name='input_output_intervals')
    DFconnectionMatrix = pd.read_excel(loc, sheet_name='connection_matrix', index_col=0)
    # inputs
    inputPrices = DFIntervals.input_price.to_numpy()
    posInputs = inputPrices != 0    #find where the input interval are (they have an input price)

    intervalNames = DFIntervals.process_intervals[posInputs]  # find names of input interval variable
    componentsList =  DFIntervals.components[posInputs]
    compositionsList =  DFIntervals.composition[posInputs]

    ####
    inBoundsLow = DFIntervals.lower_bound[posInputs].to_numpy()
    inBoundsUpper = DFIntervals.upper_bound[posInputs].to_numpy()
    inputPrices = inputPrices[posInputs]

    # define fixed parameters cost raw material
    inputPriceDict = {intervalNames[i]: inputPrices[i] for i in range(len(inputPrices))}  # make dictionary
    boundryDict = {intervalNames[i]: [inBoundsLow[i], inBoundsUpper[i]] for i in range(len(inputPrices))}  # make dictionary

    '''
    We need to find out which inputs are bound to boolean variables amongst the input variable themselves 
    i.e., if only certain inputs can be chosen among multiple possible inputs
    in other words we need to find the boolean variables from the connenction matrix (diagonals of the matrix) so the 
    activation equation sum(y) == 1 can be made. this is what the nex for loop is used for
    '''
    inputActivationVariables = [] # prealloccate
    for i,intervalName in enumerate(intervalNames):
        inputBoolVar = DFconnectionMatrix[intervalName][intervalName] # this is the diagonal position of the connention matrix
        if isinstance(inputBoolVar, str):
            inputActivationVariables.append(inputBoolVar)

    if inputActivationVariables: # if there exist bool inputs, make a unique list
        inputActivationVariables = list(OrderedDict.fromkeys(inputActivationVariables)) # makes a unique list (only need to difine a variable once)

    objectDictionary = {}
    #loop over all the inputs and make a class of each one
    for i, intervalName in enumerate(intervalNames):
        if i == 0: # so in the first input object the equaitons for the choice of
            inputActivationVariables4eq = inputActivationVariables
        else:
            inputActivationVariables4eq = []

        # pass the bool variable responsible for activating an input if present
        activationBool = []  # this is the diagonal position of the connention matrix
        if isinstance(DFconnectionMatrix[intervalName][intervalName], str):
            activationBool.append(DFconnectionMatrix[intervalName][intervalName])

        inputPrice = inputPriceDict[intervalName]
        boundryInput = boundryDict[intervalName]
        componentsOfInterval = componentsList[i].split(",")
        compositionsofInterval = compositionsList[i] # string or 1, depending if there are different components
        compsitionDictionary = {} # preallocate dictionary
        if compositionsofInterval == 1:  # if it is one, no need to loop over the dictionary, there is only one compound
            component = componentsOfInterval[0].replace(' ','')
            fraction = compositionsofInterval # should always be one component in the stream
            compsitionDictionary.update({component: fraction})
        else:
            compositionsofInterval = compositionsList[i].split(",")
            for j,component in enumerate(componentsOfInterval):
                component = component.replace(' ','')  # get rid of spaces
                fraction = compositionsofInterval[j]
                fraction = fraction.replace(' ','')
                fraction = float(fraction)
                compsitionDictionary.update({component:fraction})

        # check if it is an input to other intervals as a bool
        boolDict = {}
        processInvervalNames = DFconnectionMatrix.index.to_list()
        intervalRow = DFconnectionMatrix.loc[intervalName].to_list() # looking at the row will show to which intervals the current section is connencted to
        for j, info in enumerate(intervalRow):
            if isinstance(info,str) and 'bool' in info:
                attachInterval = processInvervalNames[j]
                boolVar = 'y_' + attachInterval + '_' + intervalName
                boolDict.update({attachInterval: boolVar})

        # create object
        objectInput = InputIntervalClass(inputName=intervalName,compositionDict=compsitionDictionary,
                                         inputActivationVariables= inputActivationVariables4eq, activationVariable= activationBool,
                                         inputPrice=inputPrice,boundryInputVar=boundryInput,boolDict= boolDict)
        objectDictionary.update({intervalName:objectInput})
    return objectDictionary

def make_reactor_intervals(excelName):
    # read Excel file
    loc = os.getcwd()
    posAlquimia = loc.find('Alquimia')
    locAlquimia = loc[0:posAlquimia + 8]
    loc = locAlquimia + r'\excel files' + excelName

    #read excel info
    DFInOutIntervals = pd.read_excel(loc, sheet_name='input_output_intervals')
    DFconnectionMatrix = pd.read_excel(loc, sheet_name='connection_matrix')
    DFreactors = pd.read_excel(loc, sheet_name='reactor_intervals')
    DFmodels =  pd.read_excel(loc, sheet_name='models')

    reactorIntervals = DFreactors.process_intervals
    objectDictionary = {} # preallcoate a dictionary with the interval names and the interval objects
    for i, intervalName in enumerate(reactorIntervals):
        intervalName = intervalName.replace(' ', '') # remove annoying spaces
        #inputs of reactor
        inputsReactor = DFreactors.inputs[i]
        inputsReactor = split_remove_spaces(inputsReactor,',')
        #outputs of the reactor
        outputsReactor = DFreactors.outputs[i]
        outputsReactor = split_remove_spaces(outputsReactor,',')
        # find the bounds of the interval
        boundsReactor = eval(DFreactors.interval_bounds[i])
        nameDict = {intervalName:boundsReactor}

        #find the equation of the reactor
        if 'xml' in DFreactors.reaction_model[i]:
            modelName = DFreactors.reaction_model[i]
            nameList = list(DFmodels.model_name)
            try:
                indexModelName = nameList.index(modelName)
            except:
                raise Exception('make sure the name {} is identical in the sheet sbml_models and reactor_intervals'.format(modelName))

            inputID = DFmodels.SBML_input_ID[indexModelName]
            outputID = DFmodels.SBML_output_ID[indexModelName]
            outputID = split_remove_spaces(outputID,',')
            equationInfo =DFmodels.iloc[indexModelName]

            equations = make_str_eq_smbl(modelName= modelName, substrate_exchange_rnx= inputID,
                                         product_exchange_rnx=outputID, equationInfo= equationInfo)
            #print('s')
        elif 'json' in DFreactors.reaction_model[i]:
            jsonFile = DFreactors.reaction_model[i]
            nameList = list(DFmodels.model_name)
            try:
                indexModelName = nameList.index(jsonFile)
            except:
                raise Exception(
                    'make sure the name for the json file {} is identical in the sheet __models__ and __reactor_interval'
                    's__'.format(jsonFile))

            jsonLoc = locAlquimia + r'\json models\{}'.format(jsonFile)
            with open(jsonLoc) as file:
                reactionObject = json.load(file)

            equationInfo = DFmodels.iloc[indexModelName]
            equations = make_str_eq_json(reactionObject,equationInfo)

        else:
            equations = DFreactors.reaction_model[i]
            equations = split_remove_spaces(equations,',')
            if not '==' in equations[0]:
                raise Exception('take a look at the reaction model mate, there is no json, xml or correct reaction given'
                                'for reactor {}'.format(intervalName))

        # find special component bounds like that for pH
        boundsComponentStr = DFreactors.input_bounds[i]
        if not isinstance(boundsComponentStr,str):
            boundsComponent = {}
        else:
            boundsComponent = str_2_dict(boundsComponentStr,intervalName)


        utilityDict = {}
        if DFreactors.has_utility[i] != 0 :
            utilityVariableNames = DFreactors.has_utility[i]
            utilityVariableNames = split_remove_spaces(utilityVariableNames,',')
            utilityPrice = DFreactors.utility_price[i]
            utilityPrice = split_remove_spaces(utilityPrice,',')
            for j, utilityName in enumerate(utilityVariableNames):
                utilityDict.update({utilityName:utilityPrice[j]})

        seperationDict = {}
        if DFreactors.seperation_coef[i] != 0: #and DFreactors.has_seperation[i] < 2 :
            outputsStr = DFreactors.outputs[i]
            coefStr = DFreactors.seperation_coef[i]
            coefList = split_remove_spaces(coefStr, ';')
            amountOfSeperations = len(coefList)
            validate_seperation_coef(coefStr,intervalName,amountOfSeperations, DFconnectionMatrix)
            for j in range(amountOfSeperations):
                seperationName = intervalName + '_sep{}'.format(j+1)
                coefTuple = stringbounds_2_tuplebounds(coefList[j])
                outputs = split_remove_spaces(outputsStr, ',' )
                specificSeperationDict = {}
                for k, outputName in enumerate(outputs):
                    specificSeperationDict.update({outputName:coefTuple[k]})
                seperationDict.update({seperationName: specificSeperationDict})
            #objectReactor.separation = seperationDict

        # check if it is mixed with other reactors
        processInvervalNames = DFconnectionMatrix.process_intervals
        reactorCol = DFconnectionMatrix[intervalName]
        pos = reactorCol != 0 # find where mixing takes place # mixed streams are in the same colunm
        mixDict = {} #preallcoation
        if sum(pos) >= 2:
            intervalsToMix = list(processInvervalNames[pos])
            specifications = list(reactorCol[pos])
            for k,specs in enumerate(specifications):
                mixDict.update({intervalsToMix[k]: specs})

                # if 'mix' in specs: # don't really need to specify if in it is mixed (very thing in a same colunm in mixed)
                    # mixDict.update({intervalsToMix[k]: specs})
            #mixDict = {intervalsToMix[j]: specifications[j] for j in range(0, len(intervalsToMix))}
            #objectReactor.mix = mixDict

        # check if it is an input to other intervals as a bool (LOOKING AT THE ROW)
        boolDict = {}
        processInvervalNames = DFconnectionMatrix['process_intervals'].to_list()
        rowIndex = processInvervalNames.index(intervalName)
        intervalRow = DFconnectionMatrix.iloc[rowIndex].to_list()  # looking at the row will show to which intervals the current section is connencted to
        # intervalRow = DFconnectionMatrix.loc[processInvervalNames == intervalName].to_dict()
        for j, info in enumerate(intervalRow):
            if isinstance(info, str) and 'bool' in info:
                attachInterval = processInvervalNames[j]
                boolVar = 'y_' + intervalName + '_' +  attachInterval
                boolDict.update({attachInterval: boolVar})

        # get the boolean variables which the reactor is dependent on (LOOKING AT THE COLUMN)
        col = reactorCol.to_list()
        boolActivationVariable = []
        boolActivationDict = {}
        inOutNames = DFInOutIntervals.process_intervals.to_list()
        # processInvervalNames is the variable with list of reactor intervalnames
        for index, infoCol in enumerate(col):
            if isinstance(infoCol,str) and 'bool' in infoCol:
                connectingInterval = processInvervalNames[index]
                boolVariable = 'y_' + intervalName + '_' + connectingInterval
                boolActivationVariable.append(boolVariable)
                if connectingInterval in inOutNames:
                    index_concented = inOutNames.index(connectingInterval)
                    inputDependent = split_remove_spaces(DFInOutIntervals.components[index_concented],',')
                else: # if it's not in the inputs/output intervals, then it is in the reactor process intervals
                    index_concented = processInvervalNames.index(connectingInterval)
                    inputDependent = split_remove_spaces(DFreactors.inputs[index_concented], ',')

                boolActivationDict.update({boolVariable:inputDependent})
        # if len(boolActivationVariable) > 1:
        #     #print('CAREFULL DOUBLE BOOL CONSTRAINTS')
        #     raise Exception("Currently the iterval bloks can only except a bool stream from one location, not multiple")

        splitList = [] # find the reactor or separation stream to split
        for j, info in enumerate(intervalRow):
            if isinstance(info, str) and 'split' in info and 'sep' in info:
                indexSep = info.find('sep')
                separationStream = info[indexSep:indexSep + 4]
                splitList.append('{}_{}'.format(intervalName,separationStream))

            elif isinstance(info, str) and 'split' in info and not 'sep' in info:
                splitList.append(intervalName)

        # trick to get unique values
        setSplits = set(splitList)
        listSplits = list(setSplits)


        # make initial interval object
        objectReactor = ReactorIntervalClass(inputs = inputsReactor, boundryInputVar = boundsComponent,
                                             outputs = outputsReactor,  reactionEquations= equations, nameDict =nameDict,
                                             mix= mixDict, utilities=utilityDict, separationDict=seperationDict,
                                             splitList= listSplits, boolActivation= boolActivationDict, boolDict= boolDict)
        # put the object in the dictionary
        objectDictionary.update({intervalName:objectReactor})
    return objectDictionary

def make_output_intervals(excelName):
    # read Excel file
    loc = os.getcwd()
    posAlquimia = loc.find('Alquimia')
    loc = loc[0:posAlquimia + 8]
    loc = loc + r'\excel files' + excelName

    #read excel info
    DFIntervals = pd.read_excel(loc, sheet_name='input_output_intervals')
    DFconnectionMatrix = pd.read_excel(loc, sheet_name='connection_matrix')

    # find the output interval names
    outputPrices = DFIntervals.output_price.to_numpy()
    posOutputs = outputPrices != 0  # find where the output interval are (they have an output price)
    intervalNames = DFIntervals.process_intervals[posOutputs]  # find names of the output interval variable

    objectDictionary = {} # preallcoate a dictionary with the interval names and the interval objects
    for i, intervalName in enumerate(intervalNames):
        intervalName = intervalName.replace(' ','') # remove spaces

        # find the bounds of the interval
        listIntervals = remove_spaces(list(DFIntervals.process_intervals))
        index = listIntervals.index(intervalName)
        lowerBound = DFIntervals.lower_bound[index]
        upperBound = DFIntervals.upper_bound[index]
        outputBound = [lowerBound,upperBound] # is this really necesary?
        outputPrice = outputPrices[index]

        # find the variable name acossiated with the output
        outputVariable = DFIntervals.components[index]
        outputVariable = outputVariable.replace(' ','')

        # check if it is mixed with other reactors
        processInvervalNames = DFconnectionMatrix.process_intervals
        reactorCol = DFconnectionMatrix[intervalName]
        pos = reactorCol != 0 # find where mixing takes place # mixed streams are in the same colunm
        mixDict = {} #preallcoation
        if sum(pos) >= 2:
            intervalsToMix = list(processInvervalNames[pos])
            specifications = list(reactorCol[pos])
            for k,specs in enumerate(specifications):
                mixDict.update({intervalsToMix[k]: specs})

        # make initial interval object
        objectReactor = OutputIntervalClass(outputName = intervalName, outputBound = outputBound,
                                            outputPrice = outputPrice, outputVariable= outputVariable, mixDict= mixDict)
        # put the object in the dictionary
        objectDictionary.update({intervalName:objectReactor})
    return objectDictionary

def define_connect_info(connectInfo):
    sepKey = ''
    splitKey = ''
    boolKey = ''
    connectKey = False
    if isinstance(connectInfo,int):
        connectKey = True
    else:
        if 'sep' in connectInfo:
            sepIndex = connectInfo.find('sep')
            sepKey = connectInfo[sepIndex: sepIndex + 4]
        if 'split' in connectInfo:
            splitIndex = connectInfo.find('split')
            splitKey = connectInfo[splitIndex: splitIndex + 6]
        if 'bool' in connectInfo:
            bIndex = connectInfo.find('split')
            boolKey = connectInfo[bIndex: bIndex + 4]

    return  connectKey, sepKey,splitKey, boolKey
# ============================================================================================================
# Functions to update the interval objects
# ============================================================================================================

def update_intervals(allIntervalObjectsDict,excelName):
    loc = os.getcwd()
    posAlquimia = loc.find('Alquimia')
    loc = loc[0:posAlquimia + 8]
    loc = loc + r'\excel files' + excelName
    # read excel info
    DFreactors = pd.read_excel(loc, sheet_name='reactor_intervals')
    connectionMatrix = pd.read_excel(loc, sheet_name='connection_matrix')
    #reactorIntervals = DFreactors.reactor_name

    pyomoEquations = []
    pyomoVariables = []
    for intervalName in allIntervalObjectsDict:
        intervalObject = allIntervalObjectsDict[intervalName]
        label = intervalObject.label
        connectedIntervals = get_connected_intervals(intervalName=intervalName, conectionMatrix=connectionMatrix)

        if label == 'reactor':
            # get the connection info if there is only one connecting interval
            simpleConcention = False
            if len(connectedIntervals) == 1:
                connectInfo = list(connectedIntervals.values())[0]
                reactorKey ,sepKey, splitKey , boolKey = define_connect_info(connectInfo)
                if reactorKey or boolKey and not sepKey or not splitKey:
                    simpleConcention = True # just connecting from one reactor to the next with the connection possibly being a bool

                #update_reactor_equations: current interval connected by 1 interval
                if simpleConcention: # and connectInfo == 1 or if it is 'bool' (does not matter)
                    previousIntervalName = list(connectedIntervals.keys())[0]
                    previousIntervalObject = allIntervalObjectsDict[previousIntervalName]
                    newReactorInputs4Interval = previousIntervalObject.leavingInterval
                    intervalObject.update_reactor_equations(newReactorInputs4Interval)

                # connected by a separation stream and splits
                if sepKey and splitKey:
                    previousIntervalName = list(connectedIntervals.keys())[0]
                    previousIntervalObject = allIntervalObjectsDict[previousIntervalName]
                    allSepVars = previousIntervalObject.leavingInterval
                    newReactorInputs4Interval = []
                    for var in allSepVars:
                        if sepKey in var and splitKey in var:
                            newReactorInputs4Interval.append(var)
                    intervalObject.update_reactor_equations(newReactorInputs4Interval)

                elif sepKey and not splitKey:
                    previousIntervalName = list(connectedIntervals.keys())[0]
                    previousIntervalObject = allIntervalObjectsDict[previousIntervalName]
                    allSepVars = previousIntervalObject.leavingInterval
                    newReactorInputs4Interval = []
                    for var in allSepVars:
                        if sepKey in var:
                            newReactorInputs4Interval.append(var)
                    intervalObject.update_reactor_equations(newReactorInputs4Interval)

                elif splitKey and not sepKey: # only splitting remains
                    previousIntervalName = list(connectedIntervals.keys())[0]
                    previousIntervalObject = allIntervalObjectsDict[previousIntervalName]
                    allSepVars = previousIntervalObject.leavingInterval
                    newReactorInputs4Interval = []
                    for var in allSepVars:
                        if splitKey in var:
                            newReactorInputs4Interval.append(var)
                    intervalObject.update_reactor_equations(newReactorInputs4Interval)

            # update_reactor_equations: current interval is connected by multiple intervals by MIXING (including mixing separated streams)
            if len(connectedIntervals) > 1: # so here is mixing
                objectDict2mix = {nameObjConect:(allIntervalObjectsDict[nameObjConect], connectedIntervals[nameObjConect]) for nameObjConect in connectedIntervals}
                intervalObject.make_mix_equations(objectDict2mix)
                newReactorInputs4Interval = intervalObject.mixingVariables
                intervalObject.update_reactor_equations(newReactorInputs4Interval)


            # update_reactor_equations: current interval is connected by a seperated stream
            # wat other
            # in the case of splitting !!!!!!

        if label == 'output':
            objectDict2mix = {nameObjConect: (allIntervalObjectsDict[nameObjConect], connectedIntervals[nameObjConect])
                              for nameObjConect in connectedIntervals}
            intervalObject.make_end_equations(objectDict2mix)


    #return pyomoVariables ,pyomoEquations

def get_vars_eqs_bounds(objectDict):
    variables = {}
    continuousVariables = []
    booleanVariables = []
    fractionVariables = []
    equations = []
    boundsContinousVars = {}
    for objName in objectDict:
        obj = objectDict[objName]
        equations += obj.pyomoEquations
        continuousVariables += obj.allVariables['continuous']
        booleanVariables += obj.allVariables['boolean']
        fractionVariables += obj.allVariables['fraction']
        boundsContinousVars = boundsContinousVars | obj.boundaries

    # remove double variables in the list of continuous variables

    unique_list_var_continous = list(OrderedDict.fromkeys(continuousVariables)) # preserves order (easier to group the equations per interval this way)
    unique_list_var_bool = list(OrderedDict.fromkeys(booleanVariables))

    # # insert the list to the set
    # variables_set = set(continuousVariables)
    # # convert the set to the list
    # unique_list_var = (list(variables_set))

    # dictionary to bundel  all the varibles
    variables = {'continuous' : unique_list_var_continous,
                 'boolean' : unique_list_var_bool,
                 'fraction': fractionVariables}


    return variables,equations, boundsContinousVars

def make_pyomo_equations(variables,equations):
    pyomoEquations = []
    for eq in equations:
        for var in variables:
            if var in eq:
                eq = eq.replace(var, "model.var['{}']".format(var))
        pyomoEquations.append(eq)

    return pyomoEquations