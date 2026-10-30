package com.dragonbuff;

import org.bukkit.plugin.java.JavaPlugin;

public class DragonBuffPlugin extends JavaPlugin {
    @Override
    public void onEnable() {
        CrystalGuard guard = new CrystalGuard(this);
        getServer().getPluginManager().registerEvents(guard, this);
        guard.start();
    }
}
