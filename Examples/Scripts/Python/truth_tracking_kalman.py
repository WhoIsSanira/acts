#!/usr/bin/env python3

from pathlib import Path
from typing import Optional

import acts
import acts.examples

u = acts.UnitConstants


def runTruthTrackingKalman(
    trackingGeometry: acts.TrackingGeometry,
    field: acts.MagneticFieldProvider,
    digiConfigFile: Path,
    outputDir: Path,
    inputParticlePath: Optional[Path] = None,
    inputHitsPath: Optional[Path] = None,
    decorators=[],
    reverseFilteringMomThreshold=0 * u.GeV,
    ptcl_truth: acts.PdgParticle = acts.PdgParticle.eMuon,
    hypo: acts.ParticleHypothesis = acts.ParticleHypothesis.muon,
    summary="tracksummary_kf.root",
    s: acts.examples.Sequencer = None,
):
    from acts.examples.simulation import (
        addParticleGun,
        ParticleConfig,
        EtaConfig,
        PhiConfig,
        MomentumConfig,
        addFatras,
        addDigitization,
        ParticleSelectorConfig,
        addDigiParticleSelection,
    )
    from acts.examples.reconstruction import (
        addSeeding,
        SeedingAlgorithm,
        addKalmanTracks,
    )

    s = s or acts.examples.Sequencer(
        events=100, numThreads=-1, logLevel=acts.logging.INFO
    )

    for d in decorators:
        s.addContextDecorator(d)

    rnd = acts.examples.RandomNumbers(seed=42)
    outputDir = Path(outputDir)

    logger = acts.logging.getLogger("Truth tracking example")

    if inputParticlePath is None:
        addParticleGun(
            s,
            ParticleConfig(num=1, pdg=ptcl_truth, randomizeCharge=True),
            EtaConfig(-3.0, 3.0, uniform=True),
            MomentumConfig(1.0 * u.GeV, 1.0 * u.GeV, transverse=True),
            PhiConfig(0.0, 360.0 * u.degree),
            vtxGen=acts.examples.GaussianVertexGenerator(
                mean=acts.Vector4(0, 0, 0, 0),
                stddev=acts.Vector4(0, 0, 0, 0),
            ),
            multiplicity=1,
            rnd=rnd,
        )
    else:
        logger.info("Reading particles from %s", inputParticlePath.resolve())
        assert inputParticlePath.exists()
        s.addReader(
            acts.examples.RootParticleReader(
                level=acts.logging.INFO,
                filePath=str(inputParticlePath.resolve()),
                outputParticles="particles_generated",
            )
        )
        s.addWhiteboardAlias("particles", "particles_generated")

    if inputHitsPath is None:
        addFatras(
            s,
            trackingGeometry,
            field,
            rnd=rnd,
            enableInteractions=True,
        )
    else:
        logger.info("Reading hits from %s", inputHitsPath.resolve())
        assert inputHitsPath.exists()
        s.addReader(
            acts.examples.RootSimHitReader(
                level=acts.logging.INFO,
                filePath=str(inputHitsPath.resolve()),
                outputSimHits="simhits",
            )
        )

    addDigitization(
        s,
        trackingGeometry,
        field,
        digiConfigFile=digiConfigFile,
        rnd=rnd,
    )

    addDigiParticleSelection(
        s,
        ParticleSelectorConfig(
            pt=(0.9 * u.GeV, None),
            measurements=(7, None),
            removeNeutral=True,
            removeSecondaries=True,
        ),
    )

    addSeeding(
        s,
        trackingGeometry,
        field,
        rnd=rnd,
        inputParticles="particles_generated",
        seedingAlgorithm=SeedingAlgorithm.TruthSmeared,
        particleHypothesis=hypo,
    )

    addKalmanTracks(
        s,
        trackingGeometry,
        field,
        reverseFilteringMomThreshold,
    )

    s.addAlgorithm(
        acts.examples.TrackSelectorAlgorithm(
            level=acts.logging.INFO,
            inputTracks="tracks",
            outputTracks="selected-tracks",
            selectorConfig=acts.TrackSelector.Config(
                minMeasurements=7,
            ),
        )
    )
    s.addWhiteboardAlias("tracks", "selected-tracks")

    # s.addWriter(
    #     acts.examples.RootTrackStatesWriter(
    #         level=acts.logging.INFO,
    #         inputTracks="tracks",
    #         inputParticles="particles_selected",
    #         inputTrackParticleMatching="track_particle_matching",
    #         inputSimHits="simhits",
    #         inputMeasurementSimHitsMap="measurement_simhits_map",
    #         filePath=str(outputDir / "trackstates_kf.root"),
    #     )
    # )

    s.addWriter(
        acts.examples.RootTrackSummaryWriter(
            level=acts.logging.INFO,
            inputTracks="tracks",
            inputParticles="particles_selected",
            inputTrackParticleMatching="track_particle_matching",
            filePath=str(outputDir / summary),
        )
    )

    # s.addWriter(
    #     acts.examples.TrackFitterPerformanceWriter(
    #         level=acts.logging.INFO,
    #         inputTracks="tracks",
    #         inputParticles="particles_selected",
    #         inputTrackParticleMatching="track_particle_matching",
    #         filePath=str(outputDir / "performance_kf.root"),
    #     )
    # )

    return s


if "__main__" == __name__:

    import argparse

    # p = argparse.ArgumentParser()
    choices = ["mu", "pi", "p", "kaon"]
    # p.add_argument("--ptcl", choices=choices)
    # p.add_argument("--hypo", choices=choices)
    # args = p.parse_args()

    srcdir = Path(__file__).resolve().parent.parent.parent.parent

    # ODD
    from acts.examples.odd import getOpenDataDetector, getOpenDataDetectorDirectory

    geoDir = getOpenDataDetectorDirectory()
    actsDir = Path(__file__).parent.parent.parent.parent
    # acts.examples.dump_args_calls(locals())  # show python binding calls

    oddMaterialMap = geoDir / "data/odd-material-maps.root"

    oddDigiConfig = actsDir / "Examples/Configs/odd-digi-smearing-config.json"

    oddSeedingSel = actsDir / "Examples/Configs/odd-seeding-config.json"
    oddMaterialDeco = acts.IMaterialDecorator.fromFile(oddMaterialMap)

    detector = getOpenDataDetector(odd_dir=geoDir, materialDecorator=oddMaterialDeco)
    trackingGeometry = detector.trackingGeometry()

    ## GenericDetector
    # detector = acts.examples.GenericDetector()
    # trackingGeometry = detector.trackingGeometry()
    # digiConfigFile = (
    #     srcdir
    #     / "Examples/Configs/generic-digi-smearing-config.json"
    # )

    field = acts.ConstantBField(acts.Vector3(0, 0, 2 * u.T))


    for ptcl in choices:
        for hypo in choices:
            print(ptcl, hypo)

            s = acts.examples.Sequencer(events=10000, numThreads=-1, logLevel=acts.logging.INFO)
            
            if ptcl == "mu":
                ptcl_truth = acts.PdgParticle.eMuon
            elif ptcl == "pi":
                ptcl_truth = acts.PdgParticle.ePionMinus
            elif ptcl == "p":
                ptcl_truth = acts.PdgParticle.eProton
            elif ptcl == "kaon":
                ptcl_truth = acts.PdgParticle.eKaonMinus
            else:
                raise ValueError(f"Unknown particle type: {ptcl}")

            if hypo == "mu":
                hypo2 = acts.ParticleHypothesis.muon
            elif hypo == "pi":
                hypo2 = acts.ParticleHypothesis.pion
            elif hypo == "p":
                hypo2 = acts.ParticleHypothesis.proton
            elif hypo == "kaon":
                hypo2 = acts.ParticleHypothesis.kaon
            else:
                raise ValueError(f"Unknown hypothesis: {hypo}")

            summary = f"tracksummary_kf_h_{hypo}_t_{ptcl}.root"
            print(summary)

            runTruthTrackingKalman(
                trackingGeometry=trackingGeometry,
                field=field,
                digiConfigFile=oddDigiConfig,
                outputDir=Path.cwd(),
                ptcl_truth=ptcl_truth,
                hypo=hypo2,
                summary=summary,
                s=s
            ).run()
