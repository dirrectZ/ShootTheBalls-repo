#!/usr/bin/perl -w
#
# A script to generate optimized C blitters for Simple DirectMedia Layer
# http://www.libsdl.org/

use warnings;
use strict;

my %file;

# The formats potentially supported by this script:
# SDL_PIXELFORMAT_RGB332
# SDL_PIXELFORMAT_RGB444
# SDL_PIXELFORMAT_RGB555
# SDL_PIXELFORMAT_ARGB4444
# SDL_PIXELFORMAT_ARGB1555
# SDL_PIXELFORMAT_RGB565
# SDL_PIXELFORMAT_RGB24
# SDL_PIXELFORMAT_BGR24
# SDL_PIXELFORMAT_RGB888
# SDL_PIXELFORMAT_BGR888
# SDL_PIXELFORMAT_ARGB8888
# SDL_PIXELFORMAT_RGBA8888
# SDL_PIXELFORMAT_ABGR8888
# SDL_PIXELFORMAT_BGRA8888
# SDL_PIXELFORMAT_ARGB2101010

# The formats we're actually creating blitters for:
my @src_formats = (
    "RGB888",
    "BGR888",
    "ARGB8888",
    "RGBA8888",
    "ABGR8888",
    "BGRA8888",
);
my @dst_formats = (
    "RGB888",
    "BGR888",
    "ARGB8888",
);

my %format_size = (
    "RGB888" => 4,
    "BGR888" => 4,
    "ARGB8888" => 4,
    "RGBA8888" => 4,
    "ABGR8888" => 4,
    "BGRA8888" => 4,
);

my %format_type = (
    "RGB888" => "Uint32",
    "BGR888" => "Uint32",
    "ARGB8888" => "Uint32",
    "RGBA8888" => "Uint32",
    "ABGR8888" => "Uint32",
    "BGRA8888" => "Uint32",
);

my %get_rgba_string_ignore_alpha = (
    "RGB888" => "_R = (Uint8)(_pixel >> 16); _G = (Uint8)(_pixel >> 8); _B = (Uint8)_pixel;",
    "BGR888" => "_B = (Uint8)(_pixel >> 16); _G = (Uint8)(_pixel >> 8); _R = (Uint8)_pixel;",
    "ARGB8888" => "_R = (Uint8)(_pixel >> 16); _G = (Uint8)(_pixel >> 8); _B = (Uint8)_pixel;",
    "RGBA8888" => "_R = (Uint8)(_pixel >> 24); _G = (Uint8)(_pixel >> 16); _B = (Uint8)(_pixel >> 8);",
    "ABGR8888" => "_B = (Uint8)(_pixel >> 16); _G = (Uint8)(_pixel >> 8); _R = (Uint8)_pixel;",
    "BGRA8888" => "_B = (Uint8)(_pixel >> 24); _G = (Uint8)(_pixel >> 16); _R = (Uint8)(_pixel >> 8);",
);

my %get_rgba_string = (
    "RGB888" => $get_rgba_string_ignore_alpha{"RGB888"} . " _A = 0xFF;",
    "BGR888" => $get_rgba_string_ignore_alpha{"BGR888"} . " _A = 0xFF;",
    "ARGB8888" => $get_rgba_string_ignore_alpha{"ARGB8888"} . " _A = (Uint8)(_pixel >> 24);",
    "RGBA8888" => $get_rgba_string_ignore_alpha{"RGBA8888"} . " _A = (Uint8)_pixel;",
    "ABGR8888" => $get_rgba_string_ignore_alpha{"ABGR8888"} . " _A = (Uint8)(_pixel >> 24);",
    "BGRA8888" => $get_rgba_string_ignore_alpha{"BGRA8888"} . " _A = (Uint8)_pixel;",
);

my %set_rgba_string = (
    "RGB888" => "_pixel = ((Uint32)_R << 16) | ((Uint32)_G << 8) | _B;",
    "BGR888" => "_pixel = ((Uint32)_B << 16) | ((Uint32)_G << 8) | _R;",
    "ARGB8888" => "_pixel = ((Uint32)_A << 24) | ((Uint32)_R << 16) | ((Uint32)_G << 8) | _B;",
    "RGBA8888" => "_pixel = ((Uint32)_R << 24) | ((Uint32)_G << 16) | ((Uint32)_B << 8) | _A;",
    "ABGR8888" => "_pixel = ((Uint32)_A << 24) | ((Uint32)_B << 16) | ((Uint32)_G << 8) | _R;",
    "BGRA8888" => "_pixel = ((Uint32)_B << 24) | ((Uint32)_G << 16) | ((Uint32)_R << 8) | _A;",
);

sub open_file {
    my $name = shift;
    open(FILE, ">$name.new") || die "Cant' open $name.new: $!";
    print FILE <<__EOF__;
/* DO NOT EDIT!  This file is generated by sdlgenblit.pl */
/*
  Simple DirectMedia Layer
  Copyright (C) 1997-2018 Sam Lantinga <slouken\@libsdl.org>

  This software is provided 'as-is', without any express or implied
  warranty.  In no event will the authors be held liable for any damages
  arising from the use of this software.

  Permission is granted to anyone to use this software for any purpose,
  including commercial applications, and to alter it and redistribute it
  freely, subject to the following restrictions:

  1. The origin of this software must not be misrepresented; you must not
     claim that you wrote the original software. If you use this software
     in a product, an acknowledgment in the product documentation would be
     appreciated but is not required.
  2. Altered source versions must be plainly marked as such, and must not be
     misrepresented as being the original software.
  3. This notice may not be removed or altered from any source distribution.
*/
#include "../SDL_internal.h"

/* *INDENT-OFF* */

__EOF__
}

sub close_file {
    my $name = shift;
    print FILE <<__EOF__;
/* *INDENT-ON* */

/* vi: set ts=4 sw=4 expandtab: */
__EOF__
    close FILE;
    if ( ! -f $name || system("cmp -s $name $name.new") != 0 ) {
        rename("$name.new", "$name");
    } else {
        unlink("$name.new");
    }
}

sub output_copydefs
{
    print FILE <<__EOF__;
extern SDL_BlitFuncEntry SDL_GeneratedBlitFuncTable[];
__EOF__
}

sub output_copyfuncname
{
    my $prefix = shift;
    my $src = shift;
    my $dst = shift;
    my $modulate = shift;
    my $blend = shift;
    my $scale = shift;
    my $args = shift;
    my $suffix = shift;

    print FILE "$prefix SDL_Blit_${src}_${dst}";
    if ( $modulate ) {
        print FILE "_Modulate";
    }
    if ( $blend ) {
        print FILE "_Blend";
    }
    if ( $scale ) {
        print FILE "_Scale";
    }
    if ( $args ) {
        print FILE "(SDL_BlitInfo *info)";
    }
    print FILE "$suffix";
}

sub get_rgba
{
    my $prefix = shift;
    my $format = shift;
    my $ignore_alpha = shift;

    my $string;
    if ($ignore_alpha) {
        $string = $get_rgba_string_ignore_alpha{$format};
    } else {
        $string = $get_rgba_string{$format};
    }

    $string =~ s/_/$prefix/g;
    if ( $prefix ne "" ) {
        print FILE <<__EOF__;
            ${prefix}pixel = *$prefix;
__EOF__
    } else {
        print FILE <<__EOF__;
            pixel = *src;
__EOF__
    }
    print FILE <<__EOF__;
            $string
__EOF__
}

sub set_rgba
{
    my $prefix = shift;
    my $format = shift;
    my $string = $set_rgba_string{$format};
    $string =~ s/_/$prefix/g;
    print FILE <<__EOF__;
            $string
            *dst = ${prefix}pixel;
__EOF__
}

sub output_copycore
{
    my $src = shift;
    my $dst = shift;
    my $modulate = shift;
    my $blend = shift;
    my $s = "";
    my $d = "";

    # Nice and easy...
    if ( $src eq $dst && !$modulate && !$blend ) {
        print FILE <<__EOF__;
            *dst = *src;
__EOF__
        return;
    }

    my $dst_has_alpha = ($dst =~ /A/) ? 1 : 0;
    my $ignore_dst_alpha = !$dst_has_alpha && !$blend;

    if ( $blend ) {
        get_rgba("src", $src, $ignore_dst_alpha);
        get_rgba("dst", $dst, !$dst_has_alpha);
        $s = "src";
        $d = "dst";
    } else {
        get_rgba("", $src, $ignore_dst_alpha);
    }

    if ( $modulate ) {
        print FILE <<__EOF__;
            if (flags & SDL_COPY_MODULATE_COLOR) {
                ${s}R = (${s}R * modulateR) / 255;
                ${s}G = (${s}G * modulateG) / 255;
                ${s}B = (${s}B * modulateB) / 255;
            }
__EOF__
        if (not $ignore_dst_alpha) {
            print FILE <<__EOF__;
            if (flags & SDL_COPY_MODULATE_ALPHA) {
                ${s}A = (${s}A * modulateA) / 255;
            }
__EOF__
        }
    }
    if ( $blend ) {
        print FILE <<__EOF__;
            if (flags & (SDL_COPY_BLEND|SDL_COPY_ADD)) {
                /* This goes away if we ever use premultiplied alpha */
                if (${s}A < 255) {
                    ${s}R = (${s}R * ${s}A) / 255;
                    ${s}G = (${s}G * ${s}A) / 255;
                    ${s}B = (${s}B * ${s}A) / 255;
                }
            }
            switch (flags & (SDL_COPY_BLEND|SDL_COPY_ADD|SDL_COPY_MOD)) {
            case SDL_COPY_BLEND:
                ${d}R = ${s}R + ((255 - ${s}A) * ${d}R) / 255;
                ${d}G = ${s}G + ((255 - ${s}A) * ${d}G) / 255;
                ${d}B = ${s}B + ((255 - ${s}A) * ${d}B) / 255;
__EOF__

        if ( $dst_has_alpha ) {
            print FILE <<__EOF__;
                ${d}A = ${s}A + ((255 - ${s}A) * ${d}A) / 255;
__EOF__
        }

        print FILE <<__EOF__;
                break;
            case SDL_COPY_ADD:
                ${d}R = ${s}R + ${d}R; if (${d}R > 255) ${d}R = 255;
                ${d}G = ${s}G + ${d}G; if (${d}G > 255) ${d}G = 255;
                ${d}B = ${s}B + ${d}B; if (${d}B > 255) ${d}B = 255;
                break;
            case SDL_COPY_MOD:
                ${d}R = (${s}R * ${d}R) / 255;
                ${d}G = (${s}G * ${d}G) / 255;
                ${d}B = (${s}B * ${d}B) / 255;
                break;
            }
__EOF__
    }
    if ( $blend ) {
        set_rgba("dst", $dst);
    } else {
        set_rgba("", $dst);
    }
}

sub output_copyfunc
{
    my $src = shift;
    my $dst = shift;
    my $modulate = shift;
    my $blend = shift;
    my $scale = shift;

    my $dst_has_alpha = ($dst =~ /A/) ? 1 : 0;
    my $ignore_dst_alpha = !$dst_has_alpha && !$blend;

    output_copyfuncname("static void", $src, $dst, $modulate, $blend, $scale, 1, "\n");
    print FILE <<__EOF__;
{
__EOF__
    if ( $modulate || $blend ) {
        print FILE <<__EOF__;
    const int flags = info->flags;
__EOF__
    }
    if ( $modulate ) {
        print FILE <<__EOF__;
    const Uint32 modulateR = info->r;
    const Uint32 modulateG = info->g;
    const Uint32 modulateB = info->b;
__EOF__
        if (!$ignore_dst_alpha) {
            print FILE <<__EOF__;
    const Uint32 modulateA = info->a;
__EOF__
        }
    }
    if ( $blend ) {
        print FILE <<__EOF__;
    Uint32 srcpixel;
    Uint32 srcR, srcG, srcB, srcA;
    Uint32 dstpixel;
__EOF__
        if ($dst_has_alpha) {
            print FILE <<__EOF__;
    Uint32 dstR, dstG, dstB, dstA;
__EOF__
        } else {
            print FILE <<__EOF__;
    Uint32 dstR, dstG, dstB;
__EOF__
        }
    } elsif ( $modulate || $src ne $dst ) {
        print FILE <<__EOF__;
    Uint32 pixel;
__EOF__
        if (!$ignore_dst_alpha) {
            print FILE <<__EOF__;
    Uint32 R, G, B, A;
__EOF__
        } else {
            print FILE <<__EOF__;
    Uint32 R, G, B;
__EOF__
        }
    }
    if ( $scale ) {
        print FILE <<__EOF__;
    int srcy, srcx;
    int posy, posx;
    int incy, incx;
__EOF__

    print FILE <<__EOF__;

    srcy = 0;
    posy = 0;
    incy = (info->src_h << 16) / info->dst_h;
    incx = (info->src_w << 16) / info->dst_w;

    while (info->dst_h--) {
        $format_type{$src} *src = 0;
        $format_type{$dst} *dst = ($format_type{$dst} *)info->dst;
        int n = info->dst_w;
        srcx = -1;
        posx = 0x10000L;
        while (posy >= 0x10000L) {
            ++srcy;
            posy -= 0x10000L;
        }
        while (n--) {
            if (posx >= 0x10000L) {
                while (posx >= 0x10000L) {
                    ++srcx;
                    posx -= 0x10000L;
                }
                src = ($format_type{$src} *)(info->src + (srcy * info->src_pitch) + (srcx * $format_size{$src}));
__EOF__
        print FILE <<__EOF__;
            }
__EOF__
        output_copycore($src, $dst, $modulate, $blend);
        print FILE <<__EOF__;
            posx += incx;
            ++dst;
        }
        posy += incy;
        info->dst += info->dst_pitch;
    }
__EOF__
    } else {
        print FILE <<__EOF__;

    while (info->dst_h--) {
        $format_type{$src} *src = ($format_type{$src} *)info->src;
        $format_type{$dst} *dst = ($format_type{$dst} *)info->dst;
        int n = info->dst_w;
        while (n--) {
__EOF__
        output_copycore($src, $dst, $modulate, $blend);
        print FILE <<__EOF__;
            ++src;
            ++dst;
        }
        info->src += info->src_pitch;
        info->dst += info->dst_pitch;
    }
__EOF__
    }
    print FILE <<__EOF__;
}

__EOF__
}

sub output_copyfunc_h
{
}

sub output_copyinc
{
    print FILE <<__EOF__;
#include "SDL_video.h"
#include "SDL_blit.h"
#include "SDL_blit_auto.h"

__EOF__
}

sub output_copyfunctable
{
    print FILE <<__EOF__;
SDL_BlitFuncEntry SDL_GeneratedBlitFuncTable[] = {
__EOF__
    for (my $i = 0; $i <= $#src_formats; ++$i) {
        my $src = $src_formats[$i];
        for (my $j = 0; $j <= $#dst_formats; ++$j) {
            my $dst = $dst_formats[$j];
            for (my $modulate = 0; $modulate <= 1; ++$modulate) {
                for (my $blend = 0; $blend <= 1; ++$blend) {
                    for (my $scale = 0; $scale <= 1; ++$scale) {
                        if ( $modulate || $blend || $scale ) {
                            print FILE "    { SDL_PIXELFORMAT_$src, SDL_PIXELFORMAT_$dst, ";
                            my $flags = "";
                            my $flag = "";
                            if ( $modulate ) {
                                $flag = "SDL_COPY_MODULATE_COLOR | SDL_COPY_MODULATE_ALPHA";
                                if ( $flags eq "" ) {
                                    $flags = $flag;
                                } else {
                                    $flags = "$flags | $flag";
                                }
                            }
                            if ( $blend ) {
                                $flag = "SDL_COPY_BLEND | SDL_COPY_ADD | SDL_COPY_MOD";
                                if ( $flags eq "" ) {
                                    $flags = $flag;
                                } else {
                                    $flags = "$flags | $flag";
                                }
                            }
                            if ( $scale ) {
                                $flag = "SDL_COPY_NEAREST";
                                if ( $flags eq "" ) {
                                    $flags = $flag;
                                } else {
                                    $flags = "$flags | $flag";
                                }
                            }
                            if ( $flags eq "" ) {
                                $flags = "0";
                            }
                            print FILE "($flags), SDL_CPU_ANY,";
                            output_copyfuncname("", $src_formats[$i], $dst_formats[$j], $modulate, $blend, $scale, 0, " },\n");
                        }
                    }
                }
            }
        }
    }
    print FILE <<__EOF__;
    { 0, 0, 0, 0, NULL }
};

__EOF__
}

sub output_copyfunc_c
{
    my $src = shift;
    my $dst = shift;

    for (my $modulate = 0; $modulate <= 1; ++$modulate) {
        for (my $blend = 0; $blend <= 1; ++$blend) {
            for (my $scale = 0; $scale <= 1; ++$scale) {
                if ( $modulate || $blend || $scale ) {
                    output_copyfunc($src, $dst, $modulate, $blend, $scale);
                }
            }
        }
    }
}

open_file("SDL_blit_auto.h");
output_copydefs();
for (my $i = 0; $i <= $#src_formats; ++$i) {
    for (my $j = 0; $j <= $#dst_formats; ++$j) {
        output_copyfunc_h($src_formats[$i], $dst_formats[$j]);
    }
}
print FILE "\n";
close_file("SDL_blit_auto.h");

open_file("SDL_blit_auto.c");
output_copyinc();
for (my $i = 0; $i <= $#src_formats; ++$i) {
    for (my $j = 0; $j <= $#dst_formats; ++$j) {
        output_copyfunc_c($src_formats[$i], $dst_formats[$j]);
    }
}
output_copyfunctable();
close_file("SDL_blit_auto.c");
