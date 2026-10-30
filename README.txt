void_dragon.bbmodel  - legged dragon (50 cubes, 'fly' animation)
void_wraith.bbmodel  - minion (14 cubes, 'fly' animation)
*.png                - textures (also embedded in the .bbmodel)
gen.py               - generator script (edit sizes/colors, rerun: python3 gen.py)

Open the .bbmodel files in Blockbench (blockbench.net) to view/edit.
Use with BetterModel or ModelEngine on Paper (Java).

---- v2 additions (nothing above was removed) ----
void_dragon.bbmodel  - now 141 cubes: brow ridges, cheek spikes, swept horns, fangs, crest, neck spines, void core,
                       shoulder/hip plates, back crystals, wing ribs + glowing veins, tail spikes + blade, leg spikes,
                       orbiting void aura. Animations: fly, idle, breath, tail_whip, dive, roar, heal
void_wraith.bbmodel  - now 38 cubes: crown, fangs, heart core, back spikes, shoulder pads, void scythe, robe, 2nd wings,
                       halo. Animations: fly, idle, attack, spawn, death
attacks/             - void_breath, void_fireball, void_lightning (PURPLE), void_shockwave, void_meteor,
                       void_heal_beam, void_spikes, void_vortex, shadow_bolt, void_slash, crystal_shield
java/CrystalGuard.java    - deepslate shell on every end crystal, many hits to break, crystal invulnerable
                            until the dragon is healing from it
java/PurpleLightning.java - purple lightning helper (particles) to use instead of vanilla lightning
gen.py               - same script, now also generates everything above (python3 gen.py)
