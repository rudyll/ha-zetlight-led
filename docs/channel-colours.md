# Channel colours — evidence and scope

Checked 2026-10-26. Chinese channel and viewing names follow the mapping confirmed
by the M5-80M owner: **A 白光, B UV 紫光, C 深蓝, D 浅蓝**.
This letter mapping is user-confirmed, not independently established by the
manufacturer diagram (which names LED groups without A–D letters).

## Manufacturer and third-party specifications

[Official M5-M product page](https://www.zetlight.com/m5-m-p00151p1.html)
contains a saltwater module diagram listing:

| Group | Manufacturer specification | Chinese label |
| --- | --- | --- |
| Cool White | 10000–15000 K | 白光 |
| UV Violet | 410–420 nm | UV 紫光 |
| Royal Blue | 440–450 nm | 深蓝 |
| Ice Blue | 470–475 nm | 浅蓝 |

[Official module diagram](https://ueeshop.ly200-cdn.com/u_file/UPAJ/UPAJ261/2609/photo/d510eb07a1.jpg)
was downloaded directly from the official page and visually inspected. Its SHA-256:
`1479056e1b1e372ecc8b2bf44579811a9306010686f41dd94ba2565d16c2cc71`.
The manufacturer presents these groups for the M5-M marine family, alongside
multiple lengths. This supports shared group descriptions within that family;
it is not a separate measurement or A–D verification of every size/revision.

[Jungle Aquatics M5 Marine specifications](https://jungleaquatics.com/products/zetlight-m5-marine-light)
list the same four groups and wavelength ranges, including the 80M variant.
This is a retailer specification, not independent spectral measurement, and may
repeat the manufacturer's material. No independent measured A–D spectrum was
established in this review. “UV Violet” is the manufacturer's group name;
410–420 nm must not be presented as measured output from an individual lamp.

## Compatibility and limitations

The integration is hardware-tested on M5-80M. These Chinese defaults describe that
mapping, not a validated universal colour map for every Zetlight family, planted
variant or firmware. Other models must verify their channel order. Protocol
channel count/device code alone does not establish LED colour. Existing user-set
names remain user-set. Raw sensors remain generic letter labels.

This correction changes labels and documentation only. Entity unique IDs,
translation keys, indices, intensities, stored schedules, viewing defaults and
lightning output are unchanged. The legacy viewing mix is not a newly recommended
spectrum. The incorrect “white+blue/no purple” lightning description is corrected to A+B
(white + UV violet on M5-80M). The effect still drives the same channels; changing
its spectral behaviour remains a separate proposal.

The optional moonlight blueprint now uses role-based selectors instead of
incorrect fixed-letter colours. Input IDs and actions remain unchanged. Existing
instances are NOT rebound: verify the moonlight output manually (M5-M B is UV
violet, C is deep blue), and ensure output/off-channel selections are distinct.
No blueprint is enabled or installed by this source correction.

## Verification / delivery

Source-only correction; no HA access, entity metadata writes, install, restart,
publication or device commands in this task. Release version remains 0.24.0;
Unreleased notes identify the pending change. Live names require a separately
approved release/install, or explicitly scoped entity-name metadata update.
