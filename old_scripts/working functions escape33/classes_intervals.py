'''
Created on Tue Oct 04 2022
Contains the classes to make the process interval objects

@author: Lucas Van der Hauwaert
email: lucas.vanderhauwaert@usc.es
'''

# ============================================================================================================
# Input, reactor and output Classes
# ============================================================================================================
# from f_makeIntervalObjects import define_connect_info
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

class InputIntervalClass:
    def __init__(self, inputName, compositionDict, inputPrice, boundryInputVar ,boolDict = None,
                 split=None, separationDict=None, inputActivationVariables= None, activationVariable= None):
        if separationDict is None:
            separationDict = {}
        if split is None:
            split = []
        if boolDict is None:
            boolDict = {}
        if inputActivationVariables is None:
            inputActivationVariables =[]
        if activationVariable is None :
            activationVariable = []


        # declare (preallocate) empty pyomo equations list
        pyomoEq = []

        # declare input interval name
        self.label = 'input'
        self.inputName = inputName.upper() # nah don't put in capitals
        self.inputPrice = inputPrice
        addOn4Variables = '_' + inputName.lower()

        # initial Boundry dictionary of all the variables (add where aprropriate )
        self.allBoundries = {}

        # change the composition names in the dictionary
        compositionDictNew = {}
        initialCompositionNames = []
        for i in compositionDict:
            compositionDictNew.update({i + addOn4Variables: compositionDict[i]})
            initialCompositionNames.append(i)
        #self.initialCompositionNames = initialCompositionNames
        self.compositionDict = compositionDictNew

        # error if you choose a wrong name
        for i in initialCompositionNames:  # maybe don't place the warning here
            if i in inputName:
                raise Exception("the component {} is in interval name {}, change the component name of the reactor to "
                                "avoid conflict with the equations".format(inputName, i))

        # make the component equations as string equations
        eqList = []
        for component in compositionDictNew:
            eq = "{} == {} * {}".format(component, self.compositionDict[component], self.inputName)
            eqPy = "model.var['{}'] == {} * model.var['{}']".format(component, self.compositionDict[component], self.inputName)
            eqList.append(eq)
            pyomoEq.append(eqPy)
        self.componentEquations = eqList
        componentVariables =  list(compositionDictNew.keys())


        self.boolDict = boolDict # necesary?
        self.split = split # necesary?
        self.separationDict = separationDict # necesary?
        self.leavingInterval = componentVariables


        eqSumOfBools = [] # empty if there is no bool equation
        if boolDict:
            eqSumOfBoolsHelp = "1 == "
            eqPyBool = "1 == "
            for interval in boolDict:
                eqSumOfBoolsHelp += " + " + boolDict[interval]
                eqPyBool += " + " + "model.boolVar['{}']".format(boolDict[interval])
            eqSumOfBools = [eqSumOfBoolsHelp]
            pyomoEq.append(eqPyBool)
        self.eqSumOfBools = eqSumOfBools

        # activation of an input by a inputActivationVariable (i.e., a boolean variable) (choice between one substrate or another)

        if inputActivationVariables: # if it's not empty make the sum equation (only the first input object makes this equation)
            sumInputActivationEqPyo = "1 == "
            for var in inputActivationVariables:
                sumInputActivationEqPyo += " + " + "model.boolVar['{}']".format(var)
            pyomoEq.append(sumInputActivationEqPyo)

        if activationVariable:
            activationEqPyoUB = "model.var['{}'] <= {} * model.boolVar['{}'] ".format(self.inputName, boundryInputVar[1],activationVariable[0])
            activationEqPyoLB = "{} * model.boolVar['{}']  <= model.var['{}'] ".format(boundryInputVar[0], activationVariable[0],self.inputName)
            pyomoEq.append(activationEqPyoLB)
            pyomoEq.append(activationEqPyoUB)


        #  put all VARIABLES that pyomo needs to declare here
        boolVariables = list(boolDict.values()) + inputActivationVariables
        continuousVariables = componentVariables + [self.inputName]


        self.allVariables = {'continuous' : continuousVariables,
                             'boolean' : boolVariables,
                             'fraction': []}
                                # fraction variables

        # make BOUNDRIES for all variables
        boundaryDict = {self.inputName: boundryInputVar}  # interval variables have bounds
        for i in componentVariables:
            boundaryDict.update({i: 'positiveReals'})
        for i in boolVariables:
            boundaryDict.update({i: 'bool'})

        self.boundaries = boundaryDict

        # put all EQUATIONS that pyomo needs to declare here
        self.allEquations = eqList + eqSumOfBools
        self.pyomoEquations = pyomoEq

    def makeOldNewDict(self, oldNames, newNames):
        oldNewDict = {oldNames[i]: newNames[i] for i in range(len(oldNames))}  # make dictionary
        self.oldNewDictOutputs = oldNewDict

    def UpdateDict(self, newKeys):
        oldDict = self.compositionDict
        oldKeys = list(oldDict.keys())
        rangeKeys = range(len(oldKeys))
        for i in rangeKeys:
            new_key = newKeys[i]
            old_key = oldKeys[i]
            self.compositionDict[new_key] = self.compositionDict.pop(old_key)

class ReactorIntervalClass:
    def __init__(self, inputs, outputs, reactionEquations, boundryInputVar ,nameDict, mix = None, utilities = None, boolActivation = None,
                 boolDict = None, splitList = None, separationDict = None):
        if utilities is None:
            utilities = {}
        if separationDict is None:
            separationDict = {}
        if boolDict is None:
            boolDict = {}
        if mix is None:
            mix = []
        if boolActivation is None:
            boolActivation = []

        # declare (preallocate) empty pyomo equations list
        pyomoEq = []

        self.label = 'reactor'
        self.nameDict = nameDict
        self.inputs = inputs  # original unmodified names
        self.outputs = outputs # original unmodified names
        self.initialCompositionNames = inputs + outputs
        # error if you choose a wrong name
        for i in self.initialCompositionNames: # maybe don't place the warning here
            if i in list(nameDict.keys())[0]:
                raise Exception("the component {} is in interval name {}, change the component name of the reactor to "
                                "avoid conflict with the equations")

        self.mix = mix  # found by the Excel file (don't need to specify in this script)
        self.utilities = utilities # consists of a dictionary {nameUtilty: [bounds]}
        self.boolDict = boolDict  # is a tuple, 1) where the bool comes from and 2) the name of the bool affecting the outputs
        self.separationDict = separationDict  # dictionary defining separation fractions of each component

        # interval Variable name
        originalIntervalName = list(self.nameDict.keys())[0]
        intervalVariable = list(self.nameDict.keys())[0].upper()
        addOn4Variables = '_' + originalIntervalName

        # reactor equations
        if isinstance(reactionEquations, str):  # failsafe if you forget to code the string reactor expression as a list
            reactionEquations = [reactionEquations]  # make it a list
        else:
            pass
        ouputs2change  = self.outputs
        allReactorEquations = []
        allReactorEquationsPyomo = []
        reactionVariablesOutput = []
        rctVarOutD = {}
        for eq in reactionEquations:
            eqPyo = eq
            for out in ouputs2change:
                newOutputName = out + '{}'.format(addOn4Variables)
                eq = eq.replace(out,newOutputName)
                # pyomo version
                newOutputNamePyo = "model.var['{}']".format(newOutputName)
                eqPyo = eqPyo.replace(out, newOutputNamePyo)


                if newOutputName not in reactionVariablesOutput:
                    reactionVariablesOutput.append(newOutputName)
                    rctVarOutD.update({out:newOutputName}) # helpìng dictionary for the serparation equations

            if boolActivation:
                for boolVar in boolActivation:
                    inputsDependent = boolActivation[boolVar]
                    for input in inputsDependent:
                        rplc = '{} * {}'.format(input,boolVar)
                        eq = eq.replace(input,rplc)
                        # pyomo version
                        rplcPyo = " {} * model.boolVar['{}'] ".format(input, boolVar)
                        eqPyo = eqPyo.replace(input, rplcPyo)

                # eq = eq.replace('==', '== (')
                # eq = eq + ') * ' + boolActivation[0]
                #
                # eqPyo = eqPyo.replace('==', '== (')
                # eqPyo = eqPyo + ') * ' + "model.boolVar['{}']".format(boolActivation[0])

            allReactorEquations.append(eq)
            allReactorEquationsPyomo.append(eqPyo)

        self.reactionEquations = allReactorEquations
        self.reactionEquationsPyomo = allReactorEquationsPyomo

        # mass equations (of the outputs from the reaction equations )
        eqMassInterval  = intervalVariable + " == "
        eqPyoMass = "model.var['{}']".format(intervalVariable) + " == "
        for out in reactionVariablesOutput:
            eqMassInterval += " + " + out
            eqPyoMass += " + " + "model.var['{}']".format(out) # pyomo version
        self.totalMassEquation =  [eqMassInterval]
        pyomoEq.append(eqPyoMass)

        # bool activation constraints
        # has been disactivated. bool variables are now in the reaction equations (solver is more efficient that way)
        boolActivationEquations = []
        # if boolActivation: # if there is an activation constraint
        #     bounds = nameDict[originalIntervalName]
        #     lowerActivationEq = "{} * {} <= {}".format(boolActivation[0],bounds[0],intervalVariable)
        #     upperActivationEq = "{} <= {} * {}".format(intervalVariable,boolActivation[0], bounds[1])
        #     boolActivationEquations.append(lowerActivationEq)
        #     boolActivationEquations.append(upperActivationEq)
        #
        #     # pyomo version
        #     lowerActivationEqPyo = "model.boolVar['{}'] * {} <= model.var['{}']".format(boolActivation[0], bounds[0], intervalVariable)
        #     upperActivationEqPyo = "model.var['{}'] <= model.boolVar['{}'] * {}".format(intervalVariable, boolActivation[0], bounds[1])
        #     pyomoEq.append(lowerActivationEqPyo)
        #     pyomoEq.append(upperActivationEqPyo)
        self.boolActivationEquations =  boolActivationEquations


        # sum of bool equations
        eqSumOfBoolsHelp = "1 == "
        eqPyBool = "1 == "
        eqSumOfBools = []  # empty if there is no bool equation
        if boolDict:
            for interval in boolDict:
                eqSumOfBoolsHelp += " + " + boolDict[interval]
                eqPyBool += " + " + "model.boolVar['{}']".format(boolDict[interval])

            eqSumOfBools = [eqSumOfBoolsHelp]
            pyomoEq.append([eqSumOfBools])
        self.eqSumOfBools = eqSumOfBools


        # separation equations
        separationEquations = []
        separationVariables = []
        for sep in separationDict: # if it is empty it should not loop nmrly
            for componentSep in separationDict[sep]:
                var = rctVarOutD[componentSep]  # helpìng dictionary to get the right variable
                sepVar  = componentSep + '_' + sep
                eqSep =  "{} == {} * {} ".format(sepVar,separationDict[sep][componentSep], var)
                separationEquations.append(eqSep)
                separationVariables.append(sepVar)

                # pyomo version
                sepVarPyo = "model.var['{}']".format(sepVar)
                eqSepPyo = "{} == {} * model.var['{}']".format(sepVarPyo,separationDict[sep][componentSep], var)
                pyomoEq.append(eqSepPyo)

        self.separationEquations = separationEquations
        self.separationVariables = separationVariables

        # spliting equations
        if splitList:
            if len(splitList) != 1 and len(splitList) != 2:
                raise Exception('look at reactor row {} in the connection matrix, it looks like you are missing a split '
                                'statement'.format(addOn4Variables))

        splitFractionVariables = []
        splitComponentVariables = []
        splittingEquations = []

        for splitStream in splitList:
            splitFractionVar = 'split_fraction_{}'.format(splitStream)
            splitFractionVariables.append(splitFractionVar)
            for component in outputs:  # the self.outputs are the original names given to the outputs of the reactor

                split1 = component + '_' + splitStream + '_' + 'split1'
                split2 = component + '_' + splitStream + '_' +'split2'
                splitComponentVariables.append(split1)
                splitComponentVariables.append(split2)

                component2split = component + '_' + splitStream
                eqSplit1 =  '{} == {} * {}'.format(split1, splitFractionVar, component2split)
                eqSplit2 = '{} == (1 - {}) * {}'.format(split2, splitFractionVar, component2split)
                splittingEquations.append([eqSplit1, eqSplit2])

                eqSplit1Pyo = "model.var['{}'] == model.fractionVar['{}'] * model.var['{}']".format(split1, splitFractionVar, component2split)
                eqSplit2Pyo = "model.var['{}'] == (1 - model.fractionVar['{}']) * model.var['{}']".format(split2, splitFractionVar, component2split)
                pyomoEq.append(eqSplit1Pyo)
                pyomoEq.append(eqSplit2Pyo)

        # mixing equations
        # see def make_mixing_equations()

        # define wat is leaving the reactor
        # can either be from the reactor, the separation process or the spliting
        if not splitList and not separationDict:
            self.leavingInterval = reactionVariablesOutput
        elif separationDict and not splitList:
            self.leavingInterval = separationVariables
        elif splitList and not separationDict:
            self.leavingInterval = splitComponentVariables
        elif splitList and separationDict:
            VariablesGoingOutSep = separationVariables.copy()
            toRemove = []
            for i in splitList:
                separationStream = ''
                if 'sep' in i:
                    indexSep = i.find('sep')
                    separationStream = i[indexSep:indexSep + 4] # the separation stream that is going te get knocked out
                for j in VariablesGoingOutSep:
                    if separationStream in j:
                        toRemove.append(j)

            # remove unwanted variables
            for i in toRemove:
                VariablesGoingOutSep.remove(i)

            self.leavingInterval = VariablesGoingOutSep + splitComponentVariables


        # put all self.VARIABLES that pyomo needs to declare here
        self.reactionVariablesOutput = reactionVariablesOutput
        # reactionVariablesInputs can be found in class function: update_reactor_equations
        self.intervalVariable = intervalVariable
        boolVariables = list(boolDict.values())
        self.boolVariables = boolVariables

        # redundant I think
        # if boolActivation: # if it is present
        #     self.activationVariable = [boolActivation[0]]
        # else:
        #     self.activationVariable = [] # just an empty list

        # define the bounds of the variables
        boundaryDict = {}  # intervals have bounds
        if not boolActivationEquations:  # if the reactor is not affected by the boolean constraint you can add it to the boundry list
            boundInterval = nameDict[originalIntervalName]
            boundaryDict.update({intervalVariable: boundInterval})
        else:
            boundaryDict.update({intervalVariable: 'positiveReals'})

        for i in reactionVariablesOutput:
            boundaryDict.update({i: 'positiveReals'})

        for i in separationVariables:
            boundaryDict.update({i: 'positiveReals'})

        for i in boolVariables:
            boundaryDict.update({i: 'bool'})

        for i in boundryInputVar: # this is for when you want to add a specifice bound to a reaction variable SEE EXCEL
            boundaryDict[i] = boundryInputVar[i]
        self.boundryInputVar = boundryInputVar

        for i in splitComponentVariables:
            boundaryDict.update({i: 'positiveReals'})

        for i in splitFractionVariables:
            boundaryDict.update({i: 'fraction'})

        self.boundaries = boundaryDict

        # make a list with all the variables
        continuousVariables = [self.intervalVariable] + self.reactionVariablesOutput + separationVariables + splitComponentVariables # self.separationVariables
        booleanVariables = self.boolVariables
                            # + self.activationVariable don't need to add this, already in the previous interval under boolVariables
        self.allVariables = {'continuous': continuousVariables,
                             'boolean': booleanVariables,
                             'fraction': splitFractionVariables}
                                # add fraction variables

        # make a list with all the equations
        self.allEquations = self.separationEquations + self.eqSumOfBools + self.boolActivationEquations + self.totalMassEquation
        self.pyomoEquations = pyomoEq


    def make_mix_equations(self, objects2mix):
        mixEquations = []
        initialInputNames = self.inputs
        intervalNames2Mix = objects2mix.keys()

        # find the leaving variables
        leavingVars = []
        for objName in objects2mix:
            obj = objects2mix[objName][0] # first element in tuple is the object
            connectInfo = objects2mix[objName][1] # first element in tuple is connection info
            reactorKey ,sepKey, splitKey , boolKey = define_connect_info(connectInfo)

            # if there is a separation process
            if isinstance(connectInfo, str) and sepKey or splitKey:
                allSepVars = obj.leavingInterval
                for var in allSepVars:
                    if sepKey and splitKey:
                        if sepKey in var and splitKey in var:
                            leavingVars.append(var)

                    if sepKey and not splitKey:
                        if sepKey in var:
                            leavingVars.append(var)

                    if splitKey and not sepKey:
                        if splitKey in var:
                            leavingVars.append(var)
            # otherwise just add the leaving variables
            else:
                leavingVars += obj.leavingInterval

        # make the equations
        mixingVariables = []
        eqMixPyo2Add = []
        for i, ins in enumerate(initialInputNames):
            intervalName = list(self.nameDict.keys())[0]
            mixVar = "{}_{}_mix".format(ins,intervalName)
            eqMix = mixVar + " == "
            startMixEq = eqMix
            # pyomo version
            mixVarPyo = "model.var['{}']".format(mixVar)
            eqMixPyo = mixVarPyo + " == "
            #startMixEqPyo = eqMixPyo
            for lvar in leavingVars:
                if ins in lvar:
                    eqMix += " + " + lvar
                    eqMixPyo += " + " + "model.var['{}']".format(lvar)
            """
            For example in the case of pH this does not come from the previous reactor!! 
            so the variable can stay as it is and no extra equations needs to be added, hence if eqMix != startMixEq:  
            """
            if eqMix != startMixEq:
                mixEquations.append(eqMix)
                mixingVariables.append(mixVar)
                eqMixPyo2Add.append(eqMixPyo)

        self.mixEquations = mixEquations
        self.mixingVariables = mixingVariables


        for i in mixingVariables:
            self.boundaries.update({i: (0, None)})

        ''' 
        # now the reaction equations need to be updated because
        # they're the mix variables are now the inputs of the reaction equations!
        # see function update_reactor_intervals & class function update_reactor_equations
        '''

        # add the variables and equations to the allVar/equations object
        self.allEquations += mixEquations
        self.allVariables['continuous'] += mixingVariables
        self.pyomoEquations += eqMixPyo2Add

    def update_reactor_equations(self, newInputs4Interval):
        initialInputs4Interval = self.inputs
        replacementDict = self.get_replacement_dict(initialInputs4Interval, newInputs4Interval)
        equationsInterval = self.reactionEquations  # the reactor equations
        equationsIntervalPyo = self.reactionEquationsPyomo

        allEquations = []
        allPyoEquations = []
        for i, eq in enumerate(equationsInterval):
            eqPyo = equationsIntervalPyo[i]
            for var in replacementDict:
                newVarName = replacementDict[var]
                eq = eq.replace(var, newVarName)
                eqPyo = eqPyo.replace(var, "model.var['{}']".format(newVarName))
            allEquations.append(eq)
            allPyoEquations.append(eqPyo)
        self.reactionEquations = allEquations
        reactionVariablesInputs = list(replacementDict.values())
        self.reactionVariablesInputs = reactionVariablesInputs

        # add the variables and equations to the allVar/equations object
        self.allEquations += allEquations
        self.allVariables['continuous'] += self.reactionVariablesInputs
        self.pyomoEquations += allPyoEquations

        # add variables to boundry dictionary
        for i in reactionVariablesInputs:
                self.boundaries.update({i: (0, None)})

        # replace the variables which have specific bounds e.g., pH variables
        boundryInputVar = self.boundryInputVar
        for i in boundryInputVar: # this is for when you want to add a specifice bound to a reaction variable SEE EXCEL
            self.boundaries[i] = boundryInputVar[i]

    def get_replacement_dict(self,initialVars, newVars):
        replacementDict = {}
        for i in initialVars:
            if i == 'pH':  #  TODO find a better way to do this: pH always stays pH_intervalName
                reactorName = list(self.nameDict.keys())[0]
                replacementDict.update({i: 'pH_{}'.format(reactorName)})
            for j in newVars:
                if i in j:  # the initial variable (of excel) is always in the new name, that's how you can find wat belongs to where
                    replacementDict.update({i: j})

        return replacementDict

class OutputIntervalClass:
    def __init__(self, outputName, outputBound ,outputPrice, outputVariable, mixDict = None):
        if mixDict is None:
            mixDict = {}
        self.label = 'output'
        outputName = outputName.upper()
        self.outputName = outputName
        self.outputPrice = outputPrice
        if outputBound[1] == 'None' or outputBound[1] == 'none':
            self.outputBound = 'positiveReal'
        else:
            self.outputBound = outputBound
        self.outputVariable = outputVariable  # eg: acetate is output name but is refered to as ace in all the reactions
        self.allVariables = {'continuous':[outputName],
                             'boolean' : [],  # there are no boolean variables for output intervals
                             'fraction': []}  # there are no fraction variables for output intervals
        self.boundaries = {outputName:self.outputBound}
    def make_end_equations(self, objects2mix):

        # find the leaving variables of the object(s) that go into the output
        leavingVars = []
        for objName in objects2mix:
            obj = objects2mix[objName][0] # first element in tuple is the object
            connectInfo = objects2mix[objName][1] # first element in tuple is connection info

            # if there is a separation process
            if isinstance(connectInfo, str) and 'sep' in connectInfo:
                allSepVars = obj.leavingInterval
                for var in allSepVars:
                    if connectInfo in var and self.outputVariable in var:
                        leavingVars.append(var)
            # otherwise just add the leaving variables
            else:
                leavingVars += obj.leavingInterval

        # make the equations
        endVar = self.outputName
        eqEnd = endVar + " == "
        pyomoEqEnd = "model.var['{}']".format(endVar) + " == "
        #startMixEq = eqEnd
        for i, lvar in enumerate(leavingVars):
            eqEnd += " + " + lvar
            pyomoEqEnd += " + " + "model.var['{}']".format(lvar)

        self.endEquations = eqEnd
        self.allEquations = [eqEnd]
        self.pyomoEquations = [pyomoEqEnd]
        #self.endVariables = endVar
