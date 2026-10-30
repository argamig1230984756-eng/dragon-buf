package com.dragonbuff; // <-- change to your plugin's package

import org.bukkit.*;
import org.bukkit.block.Block;
import org.bukkit.entity.*;
import org.bukkit.event.EventHandler;
import org.bukkit.event.EventPriority;
import org.bukkit.event.Listener;
import org.bukkit.event.block.BlockBreakEvent;
import org.bukkit.event.block.BlockExplodeEvent;
import org.bukkit.event.entity.EntityDamageByEntityEvent;
import org.bukkit.event.entity.EntityDamageEvent;
import org.bukkit.event.entity.EntityExplodeEvent;
import org.bukkit.event.entity.EntityRegainHealthEvent;
import org.bukkit.plugin.java.JavaPlugin;

import java.util.*;

/**
 * Drop-in addition (removes nothing, hooks nothing of yours):
 *  1) every End crystal gets a DEEPSLATE shell (2 layers, roof + walls)
 *  2) shell blocks need HITS_REQUIRED completed breaks before they really go away
 *  3) shell blocks survive explosions (dragon, TNT, crystals)
 *  4) a crystal takes NO damage unless the dragon is healing from it right now
 *
 * Register in your onEnable():
 *     CrystalGuard guard = new CrystalGuard(this);
 *     getServer().getPluginManager().registerEvents(guard, this);
 *     guard.start();
 *
 * Paper API (uses Block#getBlockKey and Particle.DUST, 1.20.5+).
 */
public class CrystalGuard implements Listener {

    // ---- tweak these ----
    private static final int LAYERS = 2;                 // shell thickness
    private static final int HITS_REQUIRED = 12;         // completed breaks per deepslate block
    private static final long HEAL_WINDOW_MS = 3000;     // crystal stays hittable this long after a heal tick
    private static final double HEAL_SEARCH_RADIUS = 32; // vanilla dragon picks its crystal within 32 blocks

    private final JavaPlugin plugin;
    private final Set<Long> shell = new HashSet<>();                 // block keys that belong to a shell
    private final Map<Long, Integer> hits = new HashMap<>();         // block key -> completed breaks
    private final Map<UUID, Long> healingUntil = new HashMap<>();    // crystal uuid -> vulnerable until (ms)
    private final Set<UUID> shielded = new HashSet<>();              // crystals that already have a shell

    public CrystalGuard(JavaPlugin plugin) { this.plugin = plugin; }

    /** Call once from onEnable(). Scans the End regularly so respawned crystals get shells too. */
    public void start() {
        Bukkit.getScheduler().runTaskTimer(plugin, this::scan, 40L, 100L);
        Bukkit.getScheduler().runTaskTimer(plugin, this::ambient, 20L, 10L);
    }

    private void scan() {
        for (World w : Bukkit.getWorlds()) {
            if (w.getEnvironment() != World.Environment.THE_END) continue;
            for (EnderCrystal cr : w.getEntitiesByClass(EnderCrystal.class)) {
                if (shielded.add(cr.getUniqueId())) buildShell(cr);
            }
        }
        shielded.removeIf(id -> Bukkit.getEntity(id) == null);
        healingUntil.keySet().removeIf(id -> Bukkit.getEntity(id) == null);
    }

    private void buildShell(EnderCrystal cr) {
        Block c = cr.getLocation().getBlock();
        for (int layer = 1; layer <= LAYERS; layer++) {
            for (int dx = -layer; dx <= layer; dx++)
                for (int dz = -layer; dz <= layer; dz++)
                    for (int dy = 0; dy <= 2 + layer; dy++) {
                        boolean wall = Math.abs(dx) == layer || Math.abs(dz) == layer;
                        boolean roof = dy >= 2 + layer - 0 && dy == 2 + layer;
                        if (!wall && !roof) continue;               // hollow shell, no floor (bedrock is the floor)
                        Block b = c.getRelative(dx, dy, dz);
                        Material m = b.getType();
                        if (!(m.isAir() || m == Material.FIRE || m == Material.SOUL_FIRE)) continue; // never replace bedrock/obsidian/iron bars
                        b.setType(layer == 1 ? Material.DEEPSLATE : Material.COBBLED_DEEPSLATE, false);
                        shell.add(b.getBlockKey());
                    }
        }
        cr.getWorld().playSound(cr.getLocation(), Sound.BLOCK_DEEPSLATE_PLACE, 2f, 0.6f);
    }

    /** purple ambient particles on crystals that are still locked */
    private void ambient() {
        long now = System.currentTimeMillis();
        for (UUID id : shielded) {
            Entity e = Bukkit.getEntity(id);
            if (!(e instanceof EnderCrystal cr) || isVulnerable(cr, now)) continue;
            cr.getWorld().spawnParticle(Particle.DUST, cr.getLocation().add(0, 1, 0), 6, 1.2, 1.2, 1.2, 0,
                    new Particle.DustOptions(Color.fromRGB(150, 60, 255), 1.4f));
        }
    }

    private boolean isVulnerable(EnderCrystal cr, long now) {
        return healingUntil.getOrDefault(cr.getUniqueId(), 0L) > now;
    }

    // ---- the dragon heals from a crystal: unlock the nearest one for a short window ----
    @EventHandler(priority = EventPriority.MONITOR, ignoreCancelled = true)
    public void onHeal(EntityRegainHealthEvent e) {
        if (!(e.getEntity() instanceof EnderDragon dragon)) return;
        if (e.getRegainReason() != EntityRegainHealthEvent.RegainReason.ENDER_CRYSTAL) return;
        EnderCrystal best = null;
        double bestD = Double.MAX_VALUE;
        for (EnderCrystal cr : dragon.getWorld().getNearbyEntitiesByType(EnderCrystal.class, dragon.getLocation(), HEAL_SEARCH_RADIUS)) {
            double d = cr.getLocation().distanceSquared(dragon.getLocation());
            if (d < bestD) { bestD = d; best = cr; }
        }
        if (best == null) return;
        healingUntil.put(best.getUniqueId(), System.currentTimeMillis() + HEAL_WINDOW_MS);
        best.getWorld().spawnParticle(Particle.DUST, best.getLocation().add(0, 1, 0), 25, 1, 1, 1, 0,
                new Particle.DustOptions(Color.fromRGB(255, 80, 255), 1.8f));
    }

    // ---- crystals take no damage unless they are the one healing the dragon ----
    @EventHandler(priority = EventPriority.HIGHEST)
    public void onCrystalDamage(EntityDamageEvent e) {
        if (!(e.getEntity() instanceof EnderCrystal cr)) return;
        if (isVulnerable(cr, System.currentTimeMillis())) return;
        e.setCancelled(true);
        Player p = null;
        if (e instanceof EntityDamageByEntityEvent ed) {
            if (ed.getDamager() instanceof Player pl) p = pl;
            else if (ed.getDamager() instanceof Projectile pr && pr.getShooter() instanceof Player pl) p = pl;
        }
        if (p != null) {
            p.sendActionBar(net.kyori.adventure.text.Component.text(
                    "The crystal is sealed by the void - wait until the dragon heals from it!",
                    net.kyori.adventure.text.format.NamedTextColor.DARK_PURPLE));
            p.playSound(p.getLocation(), Sound.BLOCK_DEEPSLATE_HIT, 1f, 0.7f);
        }
    }

    // ---- deepslate shell: many hits needed ----
    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onShellBreak(BlockBreakEvent e) {
        long key = e.getBlock().getBlockKey();
        if (!shell.contains(key)) return;
        int n = hits.merge(key, 1, Integer::sum);
        if (n < HITS_REQUIRED) {
            e.setCancelled(true);
            e.getPlayer().sendActionBar(net.kyori.adventure.text.Component.text(
                    "Deepslate shield " + n + " / " + HITS_REQUIRED, net.kyori.adventure.text.format.NamedTextColor.GRAY));
            e.getBlock().getWorld().playSound(e.getBlock().getLocation(), Sound.BLOCK_DEEPSLATE_BREAK, 1f, 0.8f);
            e.getBlock().getWorld().spawnParticle(Particle.BLOCK, e.getBlock().getLocation().add(.5, .5, .5), 12, .3, .3, .3,
                    e.getBlock().getBlockData());
        } else {
            shell.remove(key);
            hits.remove(key);
            e.setDropItems(false);
        }
    }

    // ---- shell survives explosions (dragon, TNT, other crystals) ----
    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onExplode(EntityExplodeEvent e) { e.blockList().removeIf(b -> shell.contains(b.getBlockKey())); }

    @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
    public void onBlockExplode(BlockExplodeEvent e) { e.blockList().removeIf(b -> shell.contains(b.getBlockKey())); }
}
