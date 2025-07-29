// This file is part of the ACTS project.
//
// Copyright (C) 2016 CERN for the benefit of the ACTS project
//
// This Source Code Form is subject to the terms of the Mozilla Public
// License, v. 2.0. If a copy of the MPL was not distributed with this
// file, You can obtain one at https://mozilla.org/MPL/2.0/.

#include "ActsExamples/Utilities/ParametricParticleGenerator.hpp"

#include "Acts/Definitions/Algebra.hpp"
#include "Acts/Definitions/ParticleData.hpp"
#include "Acts/Utilities/AngleHelpers.hpp"

#include <limits>
#include <memory>
#include <utility>

#include <HepMC3/Attribute.h>
#include <HepMC3/FourVector.h>
#include <HepMC3/GenEvent.h>
#include <HepMC3/GenParticle.h>
#include <HepMC3/GenVertex.h>

using namespace Acts::UnitLiterals;

namespace ActsExamples {

ParametricParticleGenerator::ParametricParticleGenerator(const Config& cfg)
    : m_cfg(cfg){

  m_particleChoice = UniformIndex(0u, m_cfg.pdg.size() - 1);
  m_phiDist = UniformReal(m_cfg.phiMin, m_cfg.phiMax);

  for (auto& pdg : m_cfg.pdg) {
    m_masses.push_back(cfg.mass.value_or(Acts::findMass(pdg).value_or(0)));
  }

  if (m_cfg.etaUniform) {
    double etaMin = Acts::AngleHelpers::etaFromTheta(m_cfg.thetaMin);
    double etaMax = Acts::AngleHelpers::etaFromTheta(m_cfg.thetaMax);

    UniformReal etaDist(etaMin, etaMax);

    m_sinCosThetaDist =
        [=](RandomEngine& rng) mutable -> std::pair<double, double> {
      const double eta = etaDist(rng);
      const double theta = Acts::AngleHelpers::thetaFromEta(eta);
      return {std::sin(theta), std::cos(theta)};
    };
  } else {
    // since we want to draw the direction uniform on the unit sphere, we must
    // draw from cos(theta) instead of theta. see e.g.
    // https://mathworld.wolfram.com/SpherePointPicking.html
    double cosThetaMin = std::cos(m_cfg.thetaMin);
    // ensure upper bound is included. see e.g.
    // https://en.cppreference.com/w/cpp/numeric/random/uniform_real_distribution
    double cosThetaMax = std::nextafter(std::cos(m_cfg.thetaMax),
                                        std::numeric_limits<double>::max());

    UniformReal cosThetaDist(cosThetaMin, cosThetaMax);

    m_sinCosThetaDist =
        [=](RandomEngine& rng) mutable -> std::pair<double, double> {
      const double cosTheta = cosThetaDist(rng);
      return {std::sqrt(1 - cosTheta * cosTheta), cosTheta};
    };
  }

  if (m_cfg.pLogUniform) {
    // distributes p or pt uniformly in log space
    UniformReal dist(std::log(m_cfg.pMin), std::log(m_cfg.pMax));

    m_somePDist = [=](RandomEngine& rng) mutable {
      return std::exp(dist(rng));
    };
  } else {
    // distributes p or pt uniformly
    UniformReal dist(m_cfg.pMin, m_cfg.pMax);

    m_somePDist = [=](RandomEngine& rng) mutable { return dist(rng); };
  }
}

std::shared_ptr<HepMC3::GenEvent> ParametricParticleGenerator::operator()(
    RandomEngine& rng) {
  std::cout << "ParticleGun GO" << std::endl;
  auto event = std::make_shared<HepMC3::GenEvent>();

  auto primaryVertex = std::make_shared<HepMC3::GenVertex>();
  primaryVertex->set_position(HepMC3::FourVector(0., 0., 0., 0.));
  event->add_vertex(primaryVertex);

  primaryVertex->add_attribute("acts",
                               std::make_shared<HepMC3::BoolAttribute>(true));

  // Produce pseudo beam particles
  auto beamParticle = std::make_shared<HepMC3::GenParticle>();
  beamParticle->set_momentum(HepMC3::FourVector(0., 0., 0., 0.));
  beamParticle->set_generated_mass(0.);
  beamParticle->set_pid(Acts::PdgParticle::eInvalid);
  beamParticle->set_status(4);
  primaryVertex->add_particle_in(beamParticle);

  // counter will be reused as barcode particle number which must be non-zero.
  for (std::size_t ip = 1; ip <= m_cfg.numParticles; ++ip) {
    // draw parameters
    const size_t particleIndex = m_particleChoice(rng);  
    const Acts::PdgParticle pdg = m_cfg.pdg.at(particleIndex);
    const double mass = m_masses.at(particleIndex);
    const double phi = m_phiDist(rng);
    const double someP = m_somePDist(rng);

    const auto [sinTheta, cosTheta] = m_sinCosThetaDist(rng);
    // we already have sin/cos theta. they can be used directly
    const Acts::Vector3 dir = {sinTheta * std::cos(phi),
                               sinTheta * std::sin(phi), cosTheta};

    const double p = someP * (m_cfg.pTransverse ? 1. / sinTheta : 1.);

    // construct the particle;
    Acts::Vector3 momentum = p * dir;
    auto particle = std::make_shared<HepMC3::GenParticle>();
    HepMC3::FourVector hepMcMomentum(momentum.x() / 1_GeV, momentum.y() / 1_GeV,
                                     momentum.z() / 1_GeV,
                                     std::hypot(p, mass) / 1_GeV);
    particle->set_momentum(hepMcMomentum);
    particle->set_generated_mass(mass);
    particle->set_pid(pdg);
    particle->set_status(1);

    std::cout<< pdg <<std::endl;

    event->add_particle(particle);

    particle->add_attribute("pg_seq",
                            std::make_shared<HepMC3::UIntAttribute>(ip));
    particle->add_attribute("acts",
                            std::make_shared<HepMC3::BoolAttribute>(true));

    primaryVertex->add_particle_out(particle);
  }

  return event;
}

}  // namespace ActsExamples
