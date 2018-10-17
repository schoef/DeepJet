#Standard imports

import pickle
import ROOT
import numpy as np
import os
import shutil
import uuid
import operator
from math import *
        
# DeepJet & DeepJetCore
from DeepJetCore.DataCollection import DataCollection

def ptRel(p4,axis):
    a = ROOT.TVector3(axis.Vect().X(),axis.Vect().Y(),axis.Vect().Z())
    o = ROOT.TLorentzVector(p4.Px(),p4.Py(),p4.Pz(),p4.E())
    return o.Perp(a)

def deltaPhi(phi1, phi2):
    dphi = phi2-phi1
    if  dphi > pi:
        dphi -= 2.0*pi
    if dphi <= -pi:
        dphi += 2.0*pi
    return abs(dphi)

def deltaR2(eta1, phi1, eta2, phi2):
    return deltaPhi(phi1, phi2)**2 + (eta1 - eta2)**2

def deltaR(*args, **kwargs):
    return sqrt(deltaR2(*args, **kwargs))

class TrainingInfo:

    def __init__( self, directory ):

        filename = os.path.join( directory, 'dataCollection.dc')
        file_    = open( filename, 'rb')

        self.samples    =   pickle.load(file_)
        sampleentries   =   pickle.load(file_)
        originRoots     =   pickle.load(file_)
        nsamples        =   pickle.load(file_)
        useweights      =   pickle.load(file_)
        batchsize       =   pickle.load(file_)
        dataclass       =   pickle.load(file_)
        weighter        =   pickle.load(file_)
        self._means     =   pickle.load(file_)
        file_.close()


        # Get means dictionary
        self.means = {name : (self._means[0][i], self._means[1][i]) for i, name in enumerate( self._means.dtype.names) }

        # Get DeepJetCore DataCollection
        self.dataCollection = DataCollection()
        self.dataCollection.readFromFile(filename) 

        # Reading first sample & get branch structure
        fullpath = self.dataCollection.getSamplePath(self.samples[0])
        self.dataCollection.dataclass.readIn(fullpath)
        self.branches = self.dataCollection.dataclass.branches

        print "Branches:"
        for i in range(len(self.branches)):
            print "Collection", i
            for i_b, b in enumerate(self.branches[i]):
                print "  branch %2i/%2i %40s   mean %8.5f var %8.5f" %( i, i_b, b, self.means[b][0], self.means[b][1])
            print 

class InputData:

    flavors = [ 'neutral', 'charged', 'photon',  'electron', 'muon', 'SV'] # don't change the sequence!
    lengths = [ 5, 20, 10, 3, 3, 4 ]                                       # this must be consistent with the training! 

    def __init__( self, filename, treename = "tree"):

        # read class from file
        file_= ROOT.TFile( filename )
        tree = file_.Get(treename)
        # tmp locations
        self.tmpdir = "."
        self.tmpname = "DL_reader_"+uuid.uuid4().hex
        self.tmp_filenames = [ "%s.C"%self.tmpname, "%s.h"%self.tmpname ]
        # make class
        tree.MakeClass( self.tmpname )
        file_.Close()

        # move files to tmp area
        for file in self.tmp_filenames:
            shutil.move( file, os.path.join( self.tmpdir, file ) )

        # load the newly created files as macro
        ROOT.gROOT.LoadMacro( os.path.join( self.tmpdir, self.tmpname+'.C' ) )

        # make chain (can be used with more files)
        self.chain = ROOT.TChain( treename )
        self.chain.Add( filename )

        # make instance
        self.event = getattr(ROOT, "%s" % self.tmpname )( self.chain )

        self.chain.GetEntries()
        self.init_getters()

        # dict cache for all pf candidates in the event
        self._pf_candidates = {} 
        self._nevent        = None
        self.means          = None

    # Setters to store means and branches
    def setMeans( self, means ):
        self.means = means
    def setFeatureBranches( self, feature_branches ):
        self.feature_branches = feature_branches
    def setPFBranches( self, pf_branches ):
        self.pf_branches = pf_branches

    # Clean up the tmp files
    def __del__( self ):
        import os #Interesting. os gets un-imported in the destructor :-)
        for file_ in self.tmp_filenames:
           filename = os.path.join( self.tmpdir, file_ )
           if os.path.exists( filename ):
                os.remove( filename )

    # Store a list of functors that retrieve the correct branch from the event
    def feature_getters( self, collection_name):
        # return getters, if collection_name known, otherwise create      
        if self._feature_getters.has_key(collection_name): return self._feature_getters[collection_name] 
        self._feature_getters[collection_name] = {
                          "lep_pt":operator.attrgetter(collection_name+'_pt'),
                         "lep_eta":operator.attrgetter(collection_name+'_eta'),
                         "lep_phi":operator.attrgetter(collection_name+'_phi'),
                         "lep_dxy":operator.attrgetter(collection_name+'_dxy'),
                          "lep_dz":operator.attrgetter(collection_name+'_dz'),
                        "lep_edxy":operator.attrgetter(collection_name+'_edxy'),
                         "lep_edz":operator.attrgetter(collection_name+'_edz'),
                        "lep_ip3d":operator.attrgetter(collection_name+'_ip3d'),
                       "lep_sip3d":operator.attrgetter(collection_name+'_sip3d'),
              "lep_innerTrackChi2":operator.attrgetter(collection_name+'_innerTrackChi2'),
  "lep_innerTrackValidHitFraction":operator.attrgetter(collection_name+'_innerTrackValidHitFraction'),
                     "lep_ptErrTk":operator.attrgetter(collection_name+'_ptErrTk'),
                         "lep_rho":operator.attrgetter(collection_name+'_rho'),
                       "lep_jetDR":operator.attrgetter(collection_name+'_jetDR'),
         "lep_trackerLayers_float":operator.attrgetter(collection_name+'_trackerLayers'),
           "lep_pixelLayers_float":operator.attrgetter(collection_name+'_pixelLayers'),
           "lep_trackerHits_float":operator.attrgetter(collection_name+'_trackerHits'),
              "lep_lostHits_float":operator.attrgetter(collection_name+'_lostHits'),
         "lep_lostOuterHits_float":operator.attrgetter(collection_name+'_lostOuterHits'),
                    "lep_relIso03":operator.attrgetter(collection_name+'_relIso03'),
           "lep_miniRelIsoCharged":operator.attrgetter(collection_name+'_miniRelIsoCharged'),
           "lep_miniRelIsoNeutral":operator.attrgetter(collection_name+'_miniRelIsoNeutral'),
                "lep_jetPtRatiov1":operator.attrgetter(collection_name+'_jetPtRatiov1'),
                  "lep_jetPtRelv1":operator.attrgetter(collection_name+'_jetPtRelv1'),
        "lep_segmentCompatibility":operator.attrgetter(collection_name+'_segmentCompatibility'),
          "lep_muonInnerTrkRelErr":operator.attrgetter(collection_name+'_muonInnerTrkRelErr'),
          "lep_isGlobalMuon_float":operator.attrgetter(collection_name+'_isGlobalMuon'),
           "lep_chi2LocalPosition":operator.attrgetter(collection_name+'_chi2LocalPosition'),
           "lep_chi2LocalMomentum":operator.attrgetter(collection_name+'_chi2LocalMomentum'),
             "lep_globalTrackChi2":operator.attrgetter(collection_name+'_globalTrackChi2'),
         "lep_glbTrackProbability":operator.attrgetter(collection_name+'_glbTrackProbability'),
                     "lep_trkKink":operator.attrgetter(collection_name+'_trkKink'),
           "lep_caloCompatibility":operator.attrgetter(collection_name+'_caloCompatibility'),
             "lep_nStations_float":operator.attrgetter(collection_name+'_nStations'),
        }
        return self._feature_getters[collection_name] 

    # Store a list of functors that retrieve the correct branch from the event
    def init_getters( self):
        self._feature_getters = {}

        self.pf_collection_names = { 
            "neutral":  "DL_pfCand_neutral",
            "charged":  "DL_pfCand_charged",
            "photon":   "DL_pfCand_photon",
            "muon":     "DL_pfCand_muon",
            "electron": "DL_pfCand_electron",
            "SV":       "DL_SV",
            }

        self.pf_size_getters = { key:operator.attrgetter( "n"+name ) for key, name in self.pf_collection_names.iteritems() } 

        self.pf_getters = { 'neutral':{
            "pfCand_neutral_pt_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_pt"),
           "pfCand_neutral_eta_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_eta"),
           "pfCand_neutral_phi_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_phi"),
        "pfCand_neutral_dxy_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_dxy_pf"),
         "pfCand_neutral_dz_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_dz_pf"),
   "pfCand_neutral_puppiWeight_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_puppiWeight"),
  "pfCand_neutral_hcalFraction_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_hcalFraction"),
        "pfCand_neutral_fromPV_ptRelSorted":operator.attrgetter( "DL_pfCand_neutral_fromPV"),
        },
                            'charged':{
            "pfCand_charged_pt_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_pt"),
           "pfCand_charged_eta_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_eta"),
           "pfCand_charged_phi_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_phi"),
        "pfCand_charged_dxy_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_dxy_pf"),
         "pfCand_charged_dz_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_dz_pf"),
   "pfCand_charged_puppiWeight_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_puppiWeight"),
  "pfCand_charged_hcalFraction_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_hcalFraction"),
        "pfCand_charged_fromPV_ptRelSorted":operator.attrgetter( "DL_pfCand_charged_fromPV"),
        },
                            'photon':{
             "pfCand_photon_pt_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_pt"),
            "pfCand_photon_eta_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_eta"),
            "pfCand_photon_phi_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_phi"),
         "pfCand_photon_dxy_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_dxy_pf"),
          "pfCand_photon_dz_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_dz_pf"),
    "pfCand_photon_puppiWeight_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_puppiWeight"),
   "pfCand_photon_hcalFraction_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_hcalFraction"),
         "pfCand_photon_fromPV_ptRelSorted":operator.attrgetter( "DL_pfCand_photon_fromPV"),
        },
                            'electron':{
           "pfCand_electron_pt_ptRelSorted":operator.attrgetter( "DL_pfCand_electron_pt"),
          "pfCand_electron_eta_ptRelSorted":operator.attrgetter( "DL_pfCand_electron_eta"),
          "pfCand_electron_phi_ptRelSorted":operator.attrgetter( "DL_pfCand_electron_phi"),
       "pfCand_electron_dxy_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_electron_dxy_pf"),
        "pfCand_electron_dz_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_electron_dz_pf"),
        },
                            'muon':{
               "pfCand_muon_pt_ptRelSorted":operator.attrgetter( "DL_pfCand_muon_pt"),
              "pfCand_muon_eta_ptRelSorted":operator.attrgetter( "DL_pfCand_muon_eta"),
              "pfCand_muon_phi_ptRelSorted":operator.attrgetter( "DL_pfCand_muon_phi"),
           "pfCand_muon_dxy_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_muon_dxy_pf"),
            "pfCand_muon_dz_pf_ptRelSorted":operator.attrgetter( "DL_pfCand_muon_dz_pf"),
        },
                            'SV':{
                                    "SV_pt":operator.attrgetter("DL_SV_pt"),
                                   "SV_eta":operator.attrgetter("DL_SV_eta"),
                                   "SV_phi":operator.attrgetter("DL_SV_phi"),
                                  "SV_chi2":operator.attrgetter("DL_SV_chi2"),
                                  "SV_ndof":operator.attrgetter("DL_SV_ndof"),
                                   "SV_dxy":operator.attrgetter("DL_SV_dxy"),
                                  "SV_edxy":operator.attrgetter("DL_SV_edxy"),
                                  "SV_ip3d":operator.attrgetter("DL_SV_ip3d"),
                                 "SV_eip3d":operator.attrgetter("DL_SV_eip3d"),
                                 "SV_sip3d":operator.attrgetter("DL_SV_sip3d"),
                              "SV_cosTheta":operator.attrgetter("DL_SV_cosTheta"),
                                 "SV_jetPt":operator.attrgetter("DL_SV_jetPt"),
                                "SV_jetEta":operator.attrgetter("DL_SV_jetEta"),
                                 "SV_jetDR":operator.attrgetter("DL_SV_jetDR"),
                          "SV_maxDxyTracks":operator.attrgetter("DL_SV_maxDxyTracks"),
                          "SV_secDxyTracks":operator.attrgetter("DL_SV_secDxyTracks"),
                          "SV_maxD3dTracks":operator.attrgetter("DL_SV_maxD3dTracks"),
                          "SV_secD3dTracks":operator.attrgetter("DL_SV_secD3dTracks"),
        },
    }

    # for a given lepton, read the pf candidate mask and return the PF indices
    def get_pf_indices( self, pf_type, collection_name, n_lep):
        n = self.pf_size_getters[pf_type](self.event) 
        pf_mask = getattr(self.event, "%s_%s_mask" % (self.pf_collection_names[pf_type], "selectedLeptons" if collection_name=="LepGood" else "otherLeptons" ) )
        mask_ = (1<<n_lep)
        return filter( lambda i: mask_&pf_mask[i], range(n))

    def getEntry( self, nevent ):
        self.chain.GetEntry( nevent )
        self.nevent = nevent

    def _get_all_pf_candidates( self, flavor):
        n = self.pf_size_getters[flavor](self.event)
        att_getters = self.pf_getters[flavor]
        return [ {name: getter(self.event)[i] for name, getter in self.pf_getters[flavor].iteritems()} for i in range(n) ]
    
    # cached version of get_all_pf_candidates
    @property
    def pf_candidates( self ):
        if self._nevent == self.nevent:
            return self._pf_candidates
        else:
            self._pf_candidates = {flavor: self._get_all_pf_candidates(flavor) for flavor in self.flavors}
            self._nevent = self.nevent 
            return self._pf_candidates

    # put all inputs together
    def pf_candidates_for_lepton( self, collection_name, n_lep):

        # read pf indices, then select the candidates
        pf_candidates = {}
        for flavor in self.flavors:
            pf_indices            = self.get_pf_indices( flavor, collection_name, n_lep )
            pf_candidates[flavor] = [ self.pf_candidates[flavor][i] for i in pf_indices]

            # now calculate the pf_candidate features that depend on the lepton in question
            lep_p4 = ROOT.TLorentzVector()
            lep_getters = self.feature_getters( collection_name )
            lep_p4.SetPtEtaPhiM( lep_getters["lep_pt"](self.event)[n_lep], lep_getters["lep_eta"](self.event)[n_lep], lep_getters["lep_phi"](self.event)[n_lep], 0. )

            name = "pfCand_"+flavor+"_%s_ptRelSorted" if flavor!="SV" else "SV_%s"
            ptRel_name = name%"ptRel"
            dR_name    = name%"deltaR"
            for cand in pf_candidates[flavor]:

                cand_p4 = ROOT.TLorentzVector()
                cand_p4.SetPtEtaPhiM( 
                    cand[name%"pt"], cand[name%"eta"],cand[name%"phi"],0.
                    )
                
                cand[ptRel_name] = ptRel( cand_p4, lep_p4 )
                cand[dR_name]    = deltaR( cand[name%"eta"], cand[name%"phi"], lep_getters["lep_eta"](self.event)[n_lep], lep_getters["lep_phi"](self.event)[n_lep])

            # ptRel sorting
            pf_candidates[flavor].sort( key = lambda p:-p[ptRel_name] )
 
        return pf_candidates

    def features_for_lepton( self, collection_name, n_lep):
        # read the lepton features
        return [ self.feature_getters( collection_name )[b](self.event)[n_lep] for b in self.feature_branches ]

    @property 
    def pf_norm_zero( self ):
        if not hasattr( self, "_pf_norm_zero"):
            self._pf_norm_zero = []
            for i_flavor, flavor in enumerate(self.flavors):
                cand_res = []
                for i_cand in range(self.lengths[i_flavor]):
                    branch_res = [] 
                    for b in self.pf_branches[i_flavor]:
                        branch_res.append( -self.means[b][0]/self.means[b][1] )
                    cand_res.append( branch_res )
                self._pf_norm_zero.append( cand_res )
        return self._pf_norm_zero

    @property 
    def pf_zero( self ):
        if not hasattr( self, "_pf_zero"):
            self._pf_zero = []
            for i_flavor, flavor in enumerate(self.flavors):
                cand_res = []
                for i_cand in range(self.lengths[i_flavor]):
                    branch_res = [] 
                    for b in self.pf_branches[i_flavor]:
                        branch_res.append( 0 )
                    cand_res.append( branch_res )
                self._pf_zero.append( cand_res )
        return self._pf_zero

    def prepare_inputs( self, collection_name, n_lep):
        
        features            = self.features_for_lepton( collection_name, n_lep )
        features_normalized = [ (features[i_b]-self.means[b][0])/self.means[b][1] for i_b, b in enumerate( self.feature_branches ) ]
        pf_candidates = self.pf_candidates_for_lepton( collection_name, n_lep )

        pf_norm_res = self.pf_norm_zero  
        pf_res      = self.pf_zero  
        for i_flavor, (flavor, branches) in enumerate(zip(self.flavors, self.pf_branches)):
            print "flavor %10s"%flavor,"cands %2i"%len(pf_candidates[flavor]),"max %2i"%self.lengths[i_flavor]
            for i_cand, cand in enumerate(pf_candidates[flavor][:self.lengths[i_flavor]]):
                branch_res = [] 
                for i_branch, branch in enumerate(branches):
        #            try:
                        pf_norm_res[i_flavor][i_cand][i_branch] = (cand[branch]-self.means[branch][0])/self.means[branch][1]
                        pf_res[i_flavor][i_cand][i_branch]      = cand[branch]
                        print "  flavor %10s cand %2i  branch %40s val %6.4f mean %6.4f var %6.4f norm %6.4f" % ( flavor, i_cand, branch, cand[branch], self.means[branch][0], self.means[branch][1], pf_norm_res[i_flavor][i_cand][i_branch] )
        #                branch_res.append(  (cand[b]-self.means[b][0])/self.means[b][1] )
        #            except KeyError as e:
        #                print b, "means",self.means.has_key(b), "cand",cand.has_key(b)
        #                raise e
        #        cand_res.append( branch_res )
        #    pf_res.append(cand_res)
         
        return features_normalized, pf_norm_res, pf_res 

if __name__ == "__main__": 
    # Information on the training
    training_directory = '/afs/hephy.at/data/gmoertl01/DeepLepton/trainings/muons/20181013/DYVsQCD_ptRelSorted_MuonTrainData'
    trainingInfo = TrainingInfo( training_directory )

    # Input data
    input_filename = "/afs/hephy.at/work/r/rschoefbeck/CMS/tmp/CMSSW_9_4_6_patch1/src/CMGTools/StopsDilepton/cfg/test/WZTo3LNu_amcatnlo_1/treeProducerSusySingleLepton/tree.root"
    inputData = InputData( input_filename )
    inputData.getEntry(0)

    inputData.setMeans( trainingInfo.means )
    inputData.setFeatureBranches( trainingInfo.branches[0] )
    inputData.setPFBranches( trainingInfo.branches[1:] )

    nevents = inputData.chain.GetEntries()
    for nevent in range( nevents ): 
        inputData.getEntry(nevent)
        #for i_lep in range( inputData.event.nLepGood ):
        #    if abs(inputData.event.LepGood_pdgId[i_lep])!=13: continue
        #    print "LepGood %i/%i" % (i_lep, inputData.event.nLepGood)
        #    features      =  inputData.features_for_lepton( "LepGood", 0, trainingInfo.branches[0] )
        #    features_normalized, pf_norm = inputData.prepare_inputs( "LepGood", 0)
        for i_lep in range( inputData.event.nLepOther ):
            if abs(inputData.event.LepOther_pdgId[i_lep])!=13: continue
            print "LepOther %i/%i" % (i_lep, inputData.event.nLepOther)

            features      =  inputData.features_for_lepton( "LepOther", 0 )
            features_normalized, pf_norm, pf = inputData.prepare_inputs( "LepOther", 0)
            break
        break
             
    #pf_candidates = inputData.pf_candidates_for_lepton("LepGood", 0)

    #res2 = inputData.read_inputs("LepOther", trainingInfo.branches, 0)

#iPath='/afs/hephy.at/data/gmoertl01/DeepLepton/trainfiles/v1/2016/muo/pt_15_to_inf/DYVsQCD_ptRelSorted/mini_modulo_0_trainfile_1.root'
#iFile = ROOT.TFile.Open(iPath, 'read')
#iTree = iFile.Get('tree')
#nEntries = iTree.GetEntries()
#
#branchList = [
#'lep_pt',
#'lep_eta',
#'pfCand_neutral_ptRel_ptRelSorted',
#'pfCand_charged_ptRel_ptRelSorted',
#]
#
#
#for branch in branchList:
#    valList = []
#
#    for i in xrange(nEntries):
#        iTree.GetEntry(i)
#        val = iTree.GetLeaf(branch)
#        valList.append([])
#        for j in xrange(val.GetLen()):
#            valList[i].append((val.GetValue(j)-meansDict[branch][0])/meansDict[branch][1])
#
#    print '%s %.10f %.10f %.7e' %(branch, meansDict[branch][0], meansDict[branch][1], -meansDict[branch][0]/meansDict[branch][1])
#    for val in valList:
#        print val
#
#iFile.Close()
#
        

#         pfCand_neutral_ptRel_ptRelSorted
#        pfCand_neutral_deltaR_ptRelSorted
#            pfCand_neutral_pt_ptRelSorted
#        pfCand_neutral_dxy_pf_ptRelSorted
#         pfCand_neutral_dz_pf_ptRelSorted
#   pfCand_neutral_puppiWeight_ptRelSorted
#  pfCand_neutral_hcalFraction_ptRelSorted
#        pfCand_neutral_fromPV_ptRelSorted

#DL_pfCand_neutral_pt    pt for neutral pf candidates associated : 0 at: 0x478b850
#DL_pfCand_neutral_dxy_pf    dxy for neutral pf candidates associated : 0 at: 0x478e5a0
#DL_pfCand_neutral_dz_pf dz for neutral pf candidates associated : 0 at: 0x478ec10
#DL_pfCand_neutral_puppiWeight   puppiWeight for neutral pf candidates associated : 0 at: 0x478d210
#DL_pfCand_neutral_hcalFraction  hcalFraction for neutral pf candidates associated : 0 at: 0x478d8a0
#DL_pfCand_neutral_fromPV    fromPV for neutral pf candidates associated : 0 at: 0x478df30


#         pfCand_charged_ptRel_ptRelSorted
#        pfCand_charged_deltaR_ptRelSorted
#            pfCand_charged_pt_ptRelSorted
#        pfCand_charged_dxy_pf_ptRelSorted
#         pfCand_charged_dz_pf_ptRelSorted
#   pfCand_charged_puppiWeight_ptRelSorted
#  pfCand_charged_hcalFraction_ptRelSorted
#        pfCand_charged_fromPV_ptRelSorted
#
#          pfCand_photon_ptRel_ptRelSorted
#         pfCand_photon_deltaR_ptRelSorted
#             pfCand_photon_pt_ptRelSorted
#         pfCand_photon_dxy_pf_ptRelSorted
#          pfCand_photon_dz_pf_ptRelSorted
#    pfCand_photon_puppiWeight_ptRelSorted
#   pfCand_photon_hcalFraction_ptRelSorted
#         pfCand_photon_fromPV_ptRelSorted
#
#        pfCand_electron_ptRel_ptRelSorted
#       pfCand_electron_deltaR_ptRelSorted
#           pfCand_electron_pt_ptRelSorted
#       pfCand_electron_dxy_pf_ptRelSorted
#        pfCand_electron_dz_pf_ptRelSorted
#
#            pfCand_muon_ptRel_ptRelSorted
#           pfCand_muon_deltaR_ptRelSorted
#               pfCand_muon_pt_ptRelSorted
#           pfCand_muon_dxy_pf_ptRelSorted
#            pfCand_muon_dz_pf_ptRelSorted
#
#                                    SV_pt
#                                  SV_chi2
#                                  SV_ndof
#                                   SV_dxy
#                                  SV_edxy
#                                  SV_ip3d
#                                 SV_eip3d
#                                 SV_sip3d
#                              SV_cosTheta
#                                SV_deltaR
#                                 SV_jetPt
#                                SV_jetEta
#                                 SV_jetDR
#                          SV_maxDxyTracks
#                          SV_secDxyTracks
#                          SV_maxD3dTracks
#                          SV_secD3dTracks
