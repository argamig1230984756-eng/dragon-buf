package com.dragonbuff; // <-- change to your plugin's package

import org.bukkit.*;
import org.bukkit.entity.LivingEntity;

import java.util.Random;

/**
 * PURPLE lightning. Vanilla lightning is always white/blue and cannot be recoloured server-side,
 * so this draws a jagged bolt with DUST particles (violet edge -> white-lilac core) and plays the
 * normal thunder sound. Use it instead of world.strikeLightning(...) / strikeLightningEffect(...).
 *
 *     PurpleLightning.strike(target.getLocation(), 6.0, 8.0);   // radius 6, 8 damage
 *
 * For a resource-pack look, spawn the "void_lightning" model (attacks/void_lightning.bbmodel) at the
 * same spot with BetterModel/ModelEngine and play its "strike" animation - the bolt model is purple too.
 */
public final class PurpleLightning {
    private static final Random RNG = new Random();
    private static final Particle.DustOptions EDGE = new Particle.DustOptions(Color.fromRGB(150, 40, 255), 2.2f);
    private static final Particle.DustOptions CORE = new Particle.DustOptions(Color.fromRGB(235, 210, 255), 1.4f);

    private PurpleLightning() {}

    public static void strike(Location ground, double radius, double damage) {
        World w = ground.getWorld();
        if (w == null) return;

        // jagged bolt from 40 blocks up down to the ground
        double x = ground.getX(), z = ground.getZ();
        for (double y = ground.getY() + 40; y >= ground.getY(); y -= 0.6) {
            x += (RNG.nextDouble() - 0.5) * 0.9;
            z += (RNG.nextDouble() - 0.5) * 0.9;
            Location p = new Location(w, x, y, z);
            w.spawnParticle(Particle.DUST, p, 3, 0.12, 0.05, 0.12, 0, EDGE, true);
            w.spawnParticle(Particle.DUST, p, 1, 0.03, 0.03, 0.03, 0, CORE, true);
        }
        // impact burst
        w.spawnParticle(Particle.DUST, ground, 60, radius / 3, 0.3, radius / 3, 0, EDGE, true);
        w.spawnParticle(Particle.ELECTRIC_SPARK, ground, 40, radius / 3, 0.5, radius / 3, 0.2, null, true);
        w.spawnParticle(Particle.SOUL_FIRE_FLAME, ground, 20, radius / 4, 0.2, radius / 4, 0.05, null, true);
        w.playSound(ground, Sound.ENTITY_LIGHTNING_BOLT_THUNDER, 3f, 1.4f);
        w.playSound(ground, Sound.ENTITY_LIGHTNING_BOLT_IMPACT, 3f, 0.8f);

        if (damage > 0) {
            for (var e : w.getNearbyEntities(ground, radius, radius, radius)) {
                if (e instanceof LivingEntity le && !(le instanceof org.bukkit.entity.EnderDragon)) le.damage(damage);
            }
        }
    }
}
