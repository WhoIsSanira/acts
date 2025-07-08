import numpy
import uproot
import matplotlib.pyplot as plt


if __name__ == '__main__':
    file = uproot.open("/workspaces/acts/tracksummary_kf_h_mu_t_p.root")
    efit = file["tracksummary;1"]["eT_fit"]

    raw = efit.array(library="ak")
    spectrum = []
    # for i in range(len(raw)):
        # if len(raw[i]) != 0:
            # spectrum.append(raw[i][0])

    plt.hist(raw, 100, range=(-50, 50))

    print("hallo")


    

  